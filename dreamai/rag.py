import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Type

import pymupdf
import pymupdf4llm
from lancedb.db import DBConnection as LanceDBConnection
from lancedb.embeddings import SentenceTransformerEmbeddings, get_registry
from lancedb.pydantic import LanceModel
from lancedb.pydantic import Vector as LanceVector
from lancedb.table import Table as LanceTable
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from pydantic import create_model as create_pydantic_model
from pymupdf import Pixmap

CHUNK_SIZE = 800
CHUNK_OVERLAP = 300
SEPARATORS = [r"#{1,6} ", r"```\n", r"\*{2,}", r"---+\n", r"__+\n", r"\n\n", r"\n"]
EMS_MODEL = "hkunlp/instructor-base"
DEVICE = "cuda"
TEXT_FIELD_NAME = "text"


def extract_text_from_image(image_path: str, min_len: int = 2) -> str:
    pmap = Pixmap(image_path)
    ocr = pmap.pdfocr_tobytes()
    doc = pymupdf.open("pdf", ocr)
    res = "".join([page.get_text() for page in doc.pages()])
    return res if len(res) > min_len else ""


def replace_image_tags(md_text: str, image_folder: str) -> str:
    def replace_tag(match):
        image_path = match.group(1)
        full_image_path = os.path.join(image_folder, image_path)
        return extract_text_from_image(full_image_path)

    return re.sub(r"!\[\]\((.*?)\)", replace_tag, md_text)


@dataclass
class MarkdownResult:
    markdown: str
    chunks: list[dict]


def pdf_to_md_docs(
    file_path: str | Path,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
) -> MarkdownResult:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        keep_separator=True,
        is_separator_regex=True,
    )
    with tempfile.TemporaryDirectory() as image_folder:
        md_text = replace_image_tags(
            md_text=pymupdf4llm.to_markdown(
                str(file_path),
                write_images=True,
                image_path=image_folder,
                table_strategy="lines",
            ),
            image_folder=image_folder,
        )
    return MarkdownResult(
        markdown=md_text,
        chunks=[{TEXT_FIELD_NAME: chunk} for chunk in splitter.split_text(md_text)],
    )


def get_lance_ems_model(
    name: str = EMS_MODEL, device: str = DEVICE
) -> SentenceTransformerEmbeddings:
    return get_registry().get("sentence-transformers").create(name=name, device=device)


def create_lance_schema(
    name: str,
    ems_model: SentenceTransformerEmbeddings,
    data: dict,
) -> Type[LanceModel]:
    fields = {
        TEXT_FIELD_NAME: (str, ems_model.SourceField()),
        "vector": (LanceVector(dim=ems_model.ndims()), ems_model.VectorField()),  # type: ignore
        **{
            field: (type(value), ...)
            for field, value in data.items()
            if field != TEXT_FIELD_NAME
        },
    }
    return create_pydantic_model(name, **fields, __base__=LanceModel)


def add_to_lance_table(
    db: LanceDBConnection,
    table_name: str,
    data: list[dict],
    ems_model: SentenceTransformerEmbeddings | str,
    schema: Type[LanceModel] | None = None,
    ems_model_device: str = DEVICE,
) -> LanceTable:
    if isinstance(ems_model, str):
        ems_model = get_lance_ems_model(name=ems_model, device=ems_model_device)
    schema = schema or create_lance_schema(
        name="LanceDoc", ems_model=ems_model, data=data[0]
    )
    if table_name in db.table_names():
        table = db.open_table(table_name)
    else:
        table = db.create_table(name=table_name, schema=schema)
    table.add(data=data)
    table.create_fts_index(field_names=TEXT_FIELD_NAME, replace=True)  # type: ignore
    return table


class TableDescription(BaseModel):
    name: str
    description: str


