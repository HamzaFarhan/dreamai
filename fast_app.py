from pathlib import Path

import lancedb
from fasthtml import common as fh
from lancedb.rerankers import ColbertReranker

from dreamai.search_actions import add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGSettings
from starlette.responses import StreamingResponse


app = fh.FastHTML()
rag_settings = RAGSettings()
creator_settings = CreatorSettings()

LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
TEXT_FIELD_NAME = rag_settings.text_field_name
MAX_SEARCH_RESULTS = rag_settings.max_search_results

# Initialize LanceDB and reranker
lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(model_name=RERANKER, column=TEXT_FIELD_NAME)

# Custom CSS for styling
custom_css = fh.Style("""
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }
    h1 { color: #2c3e50; text-align: center; }
    form { margin-bottom: 20px; }
    input[type="file"], input[type="text"] { width: 100%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }
    button { background-color: #3498db; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background-color: #2980b9; }
    #result, #search-result { background-color: #f9f9f9; padding: 15px; border-radius: 4px; margin-top: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
    th { background-color: #f2f2f2; }
    .progress-wrapper { margin-top: 10px; }
    .progress { height: 20px; }
""")


@app.get("/")
def home():
    return (
        fh.Title("PDF Query App"),
        custom_css,
        fh.Main(
            fh.H1("PDF Query App"),
            fh.Div(
                fh.H2("Upload PDFs"),
                fh.Form(
                    fh.Input(type="file", name="pdfs", multiple=True, accept=".pdf"),
                    fh.Button("Upload PDFs"),
                    hx_post="/upload",
                    hx_target="#result",
                    hx_indicator="#upload-progress",
                ),
                fh.Div(id="upload-progress", cls="progress-wrapper htmx-indicator"),
                fh.Div(id="result"),
            ),
            fh.Div(
                fh.H2("Search Documents"),
                fh.Form(
                    fh.Input(type="text", name="query", placeholder="Enter your query"),
                    fh.Button("Search"),
                    hx_post="/search",
                    hx_target="#search-result",
                    hx_indicator="#search-progress",
                ),
                fh.Div(id="search-progress", cls="progress-wrapper htmx-indicator"),
                fh.Div(id="search-result"),
            ),
        ),
    )


@app.post("/upload")
async def upload(request):
    files = await request.form()
    uploaded_files = files.getlist("pdfs")

    if not uploaded_files:
        return "No files were uploaded."

    total_files = len(uploaded_files)
    progress_bar = fh.Progress(value=0, max=100, cls="progress progress-primary w-56")

    async def progress_generator():
        for i, file in enumerate(uploaded_files, 1):
            file_path = Path("uploads") / file.filename
            file_path.parent.mkdir(exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(await file.read())

            progress = int((i / total_files) * 100)
            progress_bar.attrs["value"] = progress
            yield fh.Div(
                f"Uploading: {i}/{total_files} files",
                progress_bar,
                id="upload-progress",
            )

        yield fh.Div(
            "Processing files...",
            fh.Progress(value=100, max=100, cls="progress progress-primary w-56"),
            id="upload-progress",
        )

        add_data_with_descriptions(
            model=creator_settings.model, lance_db=lance_db, data_path="uploads"
        )

        yield fh.P(f"Uploaded and processed {total_files} files. Ready for querying.")

    return StreamingResponse(progress_generator(), media_type="text/html")


@app.post("/search")
def search(query: str):
    table = lance_db.open_table(list(lance_db.table_names())[0])
    results = (
        table.search(query=query, query_type="hybrid")
        .rerank(reranker=reranker)  # type: ignore
        .limit(MAX_SEARCH_RESULTS)
        .to_pandas()
    )

    # Convert DataFrame to HTML table with custom styling
    table_html = results.to_html(classes="table", index=False, escape=False)
    return fh.Div(
        fh.H3(f"Search Results for: {query}"), fh.NotStr(table_html), id="search-result"
    )


# Add a route for static files (CSS, JS, etc.) if needed
@app.get("/{fname:path}.{ext:static}")
def static(fname: str, ext: str):
    return fh.FileResponse(f"{fname}.{ext}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
