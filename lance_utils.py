import lancedb
from lancedb.db import DBConnection
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from lancedb.table import Table
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument
from pydantic import BaseModel, Field

LANCE_URI = "lance/rag"
EMS_MODEL = "BAAI/bge-small-en-v1.5"  # for the embeddings in LanceDB
DEVICE = "cuda"  # or "cpu"
DOCS_LIMIT = 5  # number of documents to retrieve from the database
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n"]


def pdf_to_docs(
    pdf_file: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list = SEPARATORS,
) -> list[LCDocument]:
    loader = PyPDFLoader(file_path=pdf_file)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        keep_separator=False,
    )
    docs = loader.load_and_split(splitter)
    return docs


def add_table(
    db: DBConnection,
    table_name: str,
    data: list[LCDocument],
    schema: type[LanceModel],
) -> Table:
    """
    Drop the table if it exists, create a new table, add data, and create a Full-Text Search index.
    Semenaitc Search is enabled by default. So creating an FTS index makes the table Hybrid Search ready.
    Learn more about Hybrid Search in LanceDB: https://lancedb.github.io/lancedb/hybrid_search/hybrid_search/
    """
    db.drop_table(name=table_name, ignore_missing=True)  # type: ignore
    table = db.create_table(name=table_name, schema=schema)
    table.add(data=data)
    table.create_fts_index(field_names="text")  # type: ignore
    return table


class LanceDBQuery(BaseModel):
    keywords: list[str] = Field(..., min_length=1, max_length=10)
    query: str = Field(..., min_length=10, max_length=300)

    def __str__(self) -> str:
        return ", ".join(self.keywords) + ", " + self.query


def search_lancedb(
    db: DBConnection, table_name: str, query: str, limit: int = DOCS_LIMIT
) -> list[str]:
    try:
        results = (
            db.open_table(name=table_name)
            .search(query=query, query_type="hybrid")
            .limit(limit=limit)
            .to_pandas()["text"]
            .tolist()
        )
    except Exception as e:
        print(f"Error in search_lancedb: {e}")
        results = []
    return results


# Example usage:
if __name__ == "__main__":
    lance_model = (
        get_registry()
        .get("sentence-transformers")
        .create(name=EMS_MODEL, device=DEVICE)
    )

    class LanceDoc(LanceModel):
        text: str = lance_model.SourceField()
        vector: Vector(dim=lance_model.ndims()) = lance_model.VectorField()  # type: ignore
        file_name: str

    lance_db = lancedb.connect(LANCE_URI)

    # Example of how to use the functions:
    # burr_docs = load_burr_docs(burr_docs_dir=Path("burr_docs"), doc_thresh=512)
    # burr_table = add_table(db=lance_db, table_name="burr_docs", data=burr_docs, schema=LanceDoc)

    # Example of how to search:
    # query = "What is Burr?"
    # search_results = search_lancedb(db=lance_db, table_name="burr_docs", query=query)
    # print(search_results)
