from pathlib import Path

import lancedb
from lancedb.db import DBConnection
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector
from lancedb.table import Table
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

LANCE_URI = "lance/rag"
EMS_MODEL = "BAAI/bge-small-en-v1.5"  # for the embeddings in LanceDB
DEVICE = "cuda"  # or "cpu"
DOCS_LIMIT = 5  # number of documents to retrieve from the database
DOC_THRESH = 512  # threshold for merging short documents
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def merge_short_docs(
    docs: list[str], file_name: str, doc_thresh: int = DOC_THRESH
) -> list[dict[str, str]]:
    """
    Merge short documents into longer ones for better performance.
    `file_name` is the name of the file the documents came from. It's just for metadata.
    """
    merged_docs = [{"text": docs[0], "file_name": file_name}]
    for doc in docs[1:]:
        last_text = merged_docs[-1]["text"]
        if len(last_text) <= doc_thresh:
            merged_docs[-1]["text"] = last_text.strip() + "\n" + doc
        else:
            merged_docs.append({"text": doc, "file_name": file_name})
    return merged_docs


def load_burr_docs(
    burr_docs_dir: Path,
    file_names: list[str] | str | None = None,
    doc_thresh: int = DOC_THRESH,
) -> list[dict[str, str]]:
    """
    Load strings from text files in `burr_docs_dir` and merge short documents.
    If `file_names` is None, load all files in the directory.
    """
    if file_names is None:
        files_iter = burr_docs_dir.glob("*.txt")
    elif isinstance(file_names, str):
        files_iter = [file_names]
    else:
        files_iter = file_names
    docs = []
    for file in files_iter:
        docs += merge_short_docs(
            docs=(burr_docs_dir / Path(file).name)
            .with_suffix(".txt")
            .read_text()
            .split("\n\n"),
            file_name=Path(file).stem,
            doc_thresh=doc_thresh,
        )
    return docs


def pdf_to_burr_docs(
    pdf_path: Path,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    separators: list[str] | None = None,
) -> list[dict[str, str]]:
    """
    Convert a PDF to a list of Burr documents using Langchain's PyPDFLoader and text splitting.
    The output format matches that of load_burr_docs().

    Args:
        pdf_path (Path): Path to the PDF file.
        chunk_size (int): The size of each text chunk (default: 1000).
        chunk_overlap (int): The overlap between chunks (default: 200).
        separators (Optional[List[str]]): Custom separators for text splitting (default: None).

    Returns:
        List[Dict[str, str]]: A list of Burr documents.
    """
    # Load the PDF using PyPDFLoader
    loader = PyPDFLoader(str(pdf_path))
    pages = loader.load()

    # Create a text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators or ["\n\n", "\n", " ", ""],
    )

    # Split the documents
    splits = text_splitter.split_documents(pages)

    # Convert Langchain documents to Burr documents
    burr_docs = []
    for split in splits:
        burr_doc = {
            "text": split.page_content,
            "file_name": pdf_path.stem,
        }
        burr_docs.append(burr_doc)

    return burr_docs


def add_table(
    db: DBConnection,
    table_name: str,
    data: list[dict[str, str]],
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
