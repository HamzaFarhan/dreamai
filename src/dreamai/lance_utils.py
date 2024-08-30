from typing import Type

import pandas as pd
from lancedb.db import DBConnection as LanceDBConnection
from lancedb.db import DBConnection as LancedbDBConnection
from lancedb.embeddings import SentenceTransformerEmbeddings, get_registry
from lancedb.pydantic import LanceModel
from lancedb.pydantic import Vector as LanceVector
from lancedb.rerankers import Reranker
from lancedb.table import Table as LanceTable
from pydantic import create_model as create_pydantic_model

from dreamai.md_utils import MarkdownChunk
from dreamai.settings import RAGAppSettings, RAGSettings

rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()

EMS_MODEL = rag_settings.ems_model
DEVICE = rag_settings.device
TEXT_FIELD_NAME = rag_settings.text_field_name
MAX_SEARCH_RESULTS = rag_settings.max_search_results


def get_lance_ems_model(
    name: str = EMS_MODEL, device: str = DEVICE
) -> SentenceTransformerEmbeddings:
    return get_registry().get("sentence-transformers").create(name=name, device=device)


def create_lance_schema(
    ems_model: SentenceTransformerEmbeddings,
    name: str = "LanceChunk",
    metadata: dict | None = None,
) -> Type[LanceModel]:
    metadata = metadata or {}
    fields = {
        "name": (str, ...),
        "index": (int, ...),
        TEXT_FIELD_NAME: (str, ems_model.SourceField()),
        "vector": (LanceVector(dim=ems_model.ndims()), ems_model.VectorField()),  # type: ignore
        **{field: (type(value), ...) for field, value in metadata.items()},
    }
    return create_pydantic_model(name, **fields, __base__=(LanceModel))  # type: ignore


def add_to_lance_table(
    db: LanceDBConnection,
    table_name: str,
    data: list[MarkdownChunk],
    ems_model: SentenceTransformerEmbeddings | str = EMS_MODEL,
    schema: Type[LanceModel] | None = None,
    ems_model_device: str = DEVICE,
) -> LanceTable:
    if schema is None:
        if isinstance(ems_model, str):
            ems_model = get_lance_ems_model(name=ems_model, device=ems_model_device)
        schema = create_lance_schema(
            ems_model=ems_model, metadata=data[0].model_dump()["metadata"]
        )
    if table_name in db.table_names():
        table = db.open_table(table_name)
    else:
        table = db.create_table(name=table_name, schema=schema)
    table.add(
        data=[
            {**chunk.model_dump(by_alias=True, exclude={"metadata"}), **chunk.metadata}
            for chunk in data
        ]
    )
    table.create_fts_index(field_names=TEXT_FIELD_NAME, replace=True)  # type: ignore
    return table


def search_lancedb(
    db: LancedbDBConnection,
    table_name: str,
    query: list[str] | str,
    reranker: Reranker | None = None,
    max_results: int = MAX_SEARCH_RESULTS,
) -> list[dict]:
    table = db.open_table(name=table_name)
    queries = [query] if isinstance(query, str) else query

    def _searcher(q: str):
        if reranker is None:
            return table.search(query=q, query_type="hybrid")
        return table.search(query=q, query_type="hybrid").rerank(reranker=reranker)  # type:ignore

    search_results = [_searcher(q).limit(max_results).to_pandas() for q in queries]
    if len(search_results) == 0:
        return []
    results = (
        pd.concat(search_results)
        .drop_duplicates(TEXT_FIELD_NAME)
        .sort_values("_relevance_score", ascending=False)
        .reset_index(drop=True)
    )
    return [
        {k: v for k, v in d.items() if k != "vector"}
        for d in results.to_dict(orient="records")
    ]
