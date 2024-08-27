import tempfile
from pathlib import Path

import lancedb
from fastapi import UploadFile
from fasthtml.common import (
    H1,
    H2,
    Button,
    Div,
    Form,
    Input,
    Main,
    Style,
    Title,
    fast_app,
    serve,
)
from lancedb.rerankers import ColbertReranker
from rag_app import application

from dreamai.rag_utils import add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGAppSettings, RAGSettings

app = fast_app(live=True)[0]

creator_settings = CreatorSettings()
rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
HAS_WEB = rag_app_settings.has_web

lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(RERANKER) if RERANKER else None

# Global variable to store table descriptions
table_descriptions = []

# CSS styling
css = """
    .container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .ingest-section, .query-section { margin-bottom: 30px; }
    #chat-container { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
    .chat-message { margin-bottom: 10px; display: flex; flex-direction: column; }
    .chat-bubble { padding: 10px; border-radius: 10px; max-width: 70%; }
    .chat-bubble-primary { background-color: #007bff; color: white; align-self: flex-end; }
    .chat-bubble-secondary { background-color: #f1f3f5; color: black; align-self: flex-start; }
    .chat-error { color: red; }
"""


@app.get("/")
def home():
    return Title("DreamAI RAG Demo"), Main(
        Style(css),
        H1("DreamAI RAG Demo"),
        Div(
            H2("1. Ingest Data"),
            Form(
                Input(type="file", name="files", multiple=True),
                Button("Upload Files", type="submit"),
                hx_post="/ingest_files",
                hx_target="#ingest-result",
                hx_swap="innerHTML",
                enctype="multipart/form-data",
            ),
            Form(
                Input(
                    type="text",
                    name="search_query",
                    placeholder="Enter search query for data ingestion",
                ),
                Button("Ingest Data", type="submit"),
                hx_post="/ingest_query",
                hx_target="#ingest-result",
                hx_swap="innerHTML",
            ),
            Div(id="ingest-result"),
            cls="ingest-section",
        ),
        Div(
            H2("2. Query Data"),
            Div(id="chat-container"),
            Form(
                Input(type="text", name="query", placeholder="Enter your query"),
                Button("Send", type="submit"),
                hx_post="/query",
                hx_target="#chat-container",
                hx_swap="beforeend",
            ),
            cls="query-section",
        ),
        cls="container",
    )


@app.post("/ingest_files")
async def ingest_files(files: UploadFile | list[UploadFile]):
    global table_descriptions
    if not isinstance(files, list):
        files = [files]
    print(f"\n\nfiles: {files}\n\n")
    data_paths = []
    with tempfile.TemporaryDirectory() as temp_dir:
        for file in files:
            temp_file_path = Path(temp_dir) / file.filename  # type: ignore
            with open(temp_file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            data_paths.append(temp_file_path)

        table_descriptions = add_data_with_descriptions(
            model=MODEL,
            lance_db=lance_db,
            data=data_paths,
            table_descriptions=table_descriptions,
        )

    return Div(
        f"Ingested {len(data_paths)} files. Table descriptions: {table_descriptions}",
        cls="alert alert-success",
    )


@app.post("/ingest_query")
async def ingest_query(search_query: str):
    global table_descriptions
    table_descriptions = add_data_with_descriptions(
        model=MODEL,
        lance_db=lance_db,
        search_query=search_query,
        table_descriptions=table_descriptions,
    )
    return Div(
        f"Ingested data based on query. Table descriptions: {table_descriptions}",
        cls="alert alert-success",
    )


@app.post("/query")
async def query(query: str):
    global table_descriptions
    rag_app = application(
        db=lance_db,
        reranker=reranker,
        model=MODEL,
        table_descriptions=table_descriptions,
        has_web=HAS_WEB,
    )

    inputs = {"query": query}
    chat_history = []

    while True:
        step_result = rag_app.step(inputs=inputs)

        if step_result is None:
            return Div("Error: app.step() returned None", cls="chat-error")

        action, result, _ = step_result
        print(f"\n\nACTION: {action}\n\n")
        print(f"\n\nRESULT: {result}\n\n")

        if action.name == "update_chat_history":
            assistant_response = result["chat_history"][-1]["content"]
            chat_history.append(
                Div(
                    Div(inputs["query"], cls="chat-bubble chat-bubble-primary"),
                    Div(assistant_response, cls="chat-bubble chat-bubble-secondary"),
                    cls="chat-message",
                )
            )
            break
        elif action.name == "terminate":
            break

    return Div(*chat_history)


serve()
