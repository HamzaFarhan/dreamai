import json
import os
import re
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Self

import httpx
import lxml
import mammoth
import pymupdf
import pymupdf4llm
from duckduckgo_search import DDGS
from html2text import HTML2Text
from loguru import logger
from lxml.html.clean import Cleaner
from pydantic import BaseModel, Field, ValidationInfo, model_validator
from pymupdf import Pixmap
from trafilatura import extract

from dreamai.settings import RAGSettings
from dreamai.utils import _process_content, chunk_text, deindent, resolve_data_path

# pymupdf.pro.unlock()  # type: ignore

rag_settings = RAGSettings()

CHUNK_SIZE = rag_settings.chunk_size
CHUNK_OVERLAP = rag_settings.chunk_overlap
SEPARATORS = rag_settings.separators
MIN_FULL_TEXT_SIZE = rag_settings.min_full_text_size
TEXT_FIELD_NAME = rag_settings.text_field_name
MAX_SEARCH_RESULTS = rag_settings.max_search_results


class MarkdownChunk(BaseModel):
    name: str
    index: int
    text: str = Field(serialization_alias=TEXT_FIELD_NAME)
    metadata: dict = Field(default_factory=dict)


class MarkdownData(BaseModel):
    name: str
    markdown: str
    chunks: list[MarkdownChunk] = Field(default_factory=list)

    @model_validator(mode="after")
    def create_chunks(self, info: ValidationInfo) -> Self:
        if len(self.chunks) > 0:
            return self
        context = info.context or {}
        chunk_size = context.get("chunk_size", CHUNK_SIZE)
        chunk_overlap = context.get("chunk_overlap", CHUNK_OVERLAP)
        separators = context.get("separators", SEPARATORS)
        self.chunks = [
            MarkdownChunk(text=chunk, name=self.name, index=i)
            for i, chunk in enumerate(
                chunk_text(
                    text=self.markdown,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=separators,
                )
            )
        ]
        return self


def is_url(text: str) -> bool:
    return (
        re.match(
            r"^(https?:\/\/)?" r"(www\.)?[\da-z\.-]+\.[a-z]{2,}" r"([\/\w \.-]*)*\/?$", text
        )
        is not None
    )


def extract_text_from_image(image_path: str, min_len: int = 2) -> str:
    pmap = Pixmap(image_path)
    doc = pymupdf.open("pdf", pmap.pdfocr_tobytes())
    res = "".join([page.get_text() for page in doc.pages()])
    return res if len(res) > min_len else ""


def replace_image_tags(md: str, image_folder: str) -> str:
    def replace_tag(match):
        full_image_path = os.path.join(image_folder, match.group(1))
        return extract_text_from_image(full_image_path)

    return re.sub(r"!\[\]\((.*?)\)", replace_tag, md)


def remove_links_from_md(md: str) -> str:
    md = re.sub(r"!?\[([^\]]+)\]\([^\)]+\)", r"\1", md)
    md = re.sub(r"!?\[([^\]]+)\]\[[^\]]+\]", r"\1", md)
    md = re.sub(r"^\[[^\]]+\]:\s*http[s]?://\S+\s*$", "", md, flags=re.MULTILINE)
    md = re.sub(r"!?\[]\([^\)]+\)", "", md)
    return md


def remove_sponsor_related_words(text: str) -> str:
    sponsor_patterns = [
        r"\bsponsor(s|ed|ing)?\b",
        r"\bsponsorship(s)?\b",
        r"\badvertis(e|ing|ement)(s)?\b",
    ]
    for pattern in sponsor_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    return text


def clean_web_content(content: str, min_length: int = 3) -> str:
    cleaned_content = remove_sponsor_related_words(text=remove_links_from_md(md=content))
    return "\n".join(
        [line for line in cleaned_content.split("\n") if len(line.strip()) > min_length]
    )


def web_search(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list[dict]:
    return DDGS().text(query, max_results=max_results)


def get_url_body(url: str) -> str:
    body = lxml.html.fromstring(httpx.get(url).text).xpath("//body")[0]  # type: ignore
    body = Cleaner(javascript=True, style=True).clean_html(body)
    return "".join(lxml.html.tostring(c, encoding="unicode") for c in body)  # type: ignore


def url_body_to_md(body: str, extractor: str = "h2t") -> str:
    if extractor == "traf":
        body = f"<article>{body}</article>" if "<article>" not in body.lower() else body
        res = extract(
            f"<html><body>{body}</body></html>",
            output_format="markdown",
            favor_recall=True,
            include_tables=True,
            include_comments=True,
        )
    else:
        h2t = HTML2Text(bodywidth=5000)
        h2t.ignore_links = True
        h2t.mark_code = True
        h2t.ignore_images = True
        res = h2t.handle(body)

    def _f(m):
        return f"```\n{dedent(m.group(1))}\n```"

    return re.sub(r"\[code]\s*\n(.*?)\n\[/code]", _f, res or "", flags=re.DOTALL).strip()


def dict_to_md(
    content_dict: dict[str, str | Path | list[str]] | None = None,
    prefix: str = "",
    suffix: str = "",
) -> str:
    content_dict = content_dict or {}
    prompt = deindent(prefix).strip()
    for header, content in content_dict.items():
        if content:
            header = " ".join(header.split("_")).strip().title()
            content = _process_content(content).strip()
            if content:
                if prompt:
                    prompt += "\n\n"
                prompt += f"## {header}\n\n{content}"
    if suffix:
        prompt += "\n\n" + deindent(suffix).strip()
    return prompt.strip()


def docx_to_md(docx_path: str | Path) -> str:
    docx_path = str(docx_path)
    html = ""
    try:
        with open(docx_path, "rb") as docx_file:
            html = mammoth.convert_to_html(docx_file).value
    except Exception:
        logger.exception(f"Could not convert {docx_path} to html.")
    md = html
    if html:
        try:
            md = url_body_to_md(body=html)
        except Exception:
            logger.exception(f"Could not convert {docx_path} to markdown.")
    return md


def urls_to_md(
    urls: list[str] | str,
    extractor: str = "h2t",
    clean_content: bool = True,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
) -> list[MarkdownData]:
    if isinstance(urls, str):
        urls = [urls]
    urls_md = []
    for url in urls:
        md = url_body_to_md(body=get_url_body(url), extractor=extractor)
        md = clean_web_content(content=md) if clean_content else md
        urls_md.append(
            MarkdownData.model_validate(
                {"name": url, "markdown": md},
                context={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "separators": separators,
                },
            )
        )
    return urls_md


def search_query_to_md(
    query: str,
    extractor: str = "h2t",
    clean_content: bool = True,
    max_results: int = MAX_SEARCH_RESULTS,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
) -> list[MarkdownData]:
    to_md_kwargs = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "separators": separators,
    }
    search_results = web_search(query=query, max_results=max_results)
    mds = []
    for search_result in search_results:
        md = urls_to_md(
            urls=search_result["href"],
            extractor=extractor,
            clean_content=clean_content,
            **to_md_kwargs,
        ) or [
            MarkdownData.model_validate(
                {
                    "name": search_result["href"],
                    "markdown": "\n".join([search_result["title"], search_result["body"]]),
                },
                context=to_md_kwargs,
            )
        ]
        mds.extend(md)
    return mds


def docs_to_md(
    docs: list[str | Path] | str | Path,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
) -> list[MarkdownData]:
    docs_md = []
    for doc in resolve_data_path(data_path=docs):
        doc = Path(doc)
        if not doc.exists():
            md = str(doc)
        elif doc.suffix in [".md", ".txt"]:
            md = doc.read_text()
        elif doc.suffix == ".json":
            md = json.dumps(doc.read_text())
        elif doc.suffix == ".docx":
            md = docx_to_md(docx_path=doc)
        elif doc.suffix == ".pdf":
            # elif doc.suffix in [".pdf", ".doc", ".ppt", ".pptx", ".xls", ".xlsx"]:
            with tempfile.TemporaryDirectory() as image_folder:
                md = replace_image_tags(
                    md=pymupdf4llm.to_markdown(
                        doc=str(doc),
                        write_images=True,
                        image_path=image_folder,
                        table_strategy="lines",
                    ),
                    image_folder=image_folder,
                )
        else:
            md = str(doc)
        docs_md.append(
            MarkdownData.model_validate(
                {"name": doc.name, "markdown": md},
                context={
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "separators": separators,
                },
            )
        )
    return docs_md


def data_to_md(
    data: list[str | Path] | str | Path | None = None,
    search_queries: list[str] | str | None = None,
    max_results: int = MAX_SEARCH_RESULTS,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] = SEPARATORS,
) -> list[MarkdownData]:
    data = data or []
    search_queries = search_queries or []
    assert search_queries or data, "Either search_queries or data must be provided"
    to_md_kwargs = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "separators": separators,
    }
    data_md = []
    if not isinstance(search_queries, list):
        search_queries = [search_queries]
    for search_query in search_queries:
        data_md.extend(
            search_query_to_md(query=search_query, max_results=max_results, **to_md_kwargs)
        )
    if not isinstance(data, list):
        data = [data]
    for item in data:
        item = str(item)
        if is_url(item):
            data_md.extend(urls_to_md(urls=item, **to_md_kwargs))
        else:
            data_md.extend(docs_to_md(docs=item, **to_md_kwargs))
    return data_md
