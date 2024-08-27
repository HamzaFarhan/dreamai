from fasthtml.common import *
from pathlib import Path
import lancedb
from lancedb.rerankers import ColbertReranker
from dreamai.ai import ModelName
from dreamai.lance_utils import get_user_query
from dreamai.search_actions import add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGAppSettings, RAGSettings
from rag_app import application

app = FastHTML()

creator_settings = CreatorSettings()
rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
HAS_WEB = rag_app_settings.has_web

lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(RERANKER)

# CSS styling
css = """
    .container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .ingest-section, .query-section { margin-bottom: 30px; }
    #chat-container { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; margin-bottom: 10px; }
    .chat-message { margin-bottom: 10px; }
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
                action="/ingest_files", method="post", enctype="multipart/form-data"
            ),
            Form(
                Input(type="text", name="search_query", placeholder="Enter search query for data ingestion"),
                Button("Ingest Data", type="submit"),
                action="/ingest_query", method="post"
            ),
            cls="ingest-section"
        ),
        Div(
            H2("2. Query Data"),
            Div(id="chat-container"),
            Form(
                Input(type="text", name="query", placeholder="Enter your query"),
                Button("Send", type="submit"),
                action="/query", method="post", hx_post="/query", hx_target="#chat-container", hx_swap="beforeend"
            ),
            cls="query-section"
        ),
        cls="container"
    )

@app.post("/ingest_files")
async def ingest_files(files: list):
    # Process uploaded files
    data_paths = [Path(file.filename) for file in files]
    table_descriptions = add_data_with_descriptions(
        model=ModelName.GEMINI_FLASH, lance_db=lance_db, data=data_paths
    )
    return Div(f"Ingested {len(files)} files. Table descriptions: {table_descriptions}", cls="alert alert-success")

@app.post("/ingest_query")
async def ingest_query(search_query: str):
    table_descriptions = add_data_with_descriptions(
        model=ModelName.GEMINI_FLASH, lance_db=lance_db, search_query=search_query
    )
    return Div(f"Ingested data based on query. Table descriptions: {table_descriptions}", cls="alert alert-success")

@app.post("/query")
async def query(query: str):
    rag_app = application(
        db=lance_db,
        reranker=reranker,
        model=MODEL,
        table_descriptions=[],  # You might want to store and pass the actual table descriptions here
        has_web=HAS_WEB,
    )
    
    inputs = {"query": query}
    step_result = rag_app.step(inputs=inputs)
    
    if step_result is None:
        return Div("Error: app.step() returned None", cls="chat-error")
    
    action, result, _ = step_result
    
    if action.name == "update_chat_history":
        return Div(
            Div(query, cls="chat-bubble chat-bubble-primary"),
            Div(result["assistant_response"], cls="chat-bubble chat-bubble-secondary"),
            cls="chat-message"
        )
    else:
        return Div(f"Unexpected action: {action.name}", cls="chat-error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)