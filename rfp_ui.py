import json
import tempfile
from pathlib import Path

import lancedb
import pandas as pd
from docx import Document
from fastapi import File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fasthtml.common import (
    H1,
    H2,
    Button,
    Div,
    Form,
    Input,
    Main,
    Script,
    Style,
    Title,
    fast_app,
    serve,
)

from dreamai.rag import application
from dreamai.rag_utils import add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGAppSettings, RAGSettings

app = fast_app(live=True)[0]

creator_settings = CreatorSettings()
rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
LANCE_URI = "lance/RFP"
RERANKER = rag_settings.reranker
HAS_WEB = rag_app_settings.has_web

lance_db = lancedb.connect(uri=LANCE_URI)

# Global variables
table_descriptions = []
rfp_data = None
progress = {"current": 0, "total": 0}

# CSS styling
css = """
    .container { max-width: 800px; margin: 0 auto; padding: 20px; }
    .section { margin-bottom: 30px; }
    .progress-bar { width: 100%; background-color: #f0f0f0; }
    .progress-bar-fill { height: 20px; background-color: #4CAF50; width: 0%; }
    #progress-text { text-align: center; margin-top: 10px; }
"""


@app.get("/")
def home():
    return Title("RFP Processing Demo"), Main(
        Style(css),
        H1("RFP Processing Demo"),
        Div(
            H2("1. Upload Company Documents"),
            Form(
                Input(type="file", name="company_docs", multiple=True),
                Button("Upload Documents", type="submit"),
                hx_post="/upload_docs",
                hx_target="#upload-result",
                hx_swap="innerHTML",
                enctype="multipart/form-data",
            ),
            Div(id="upload-result"),
            cls="section",
        ),
        Div(
            H2("2. Upload RFP CSV File"),
            Form(
                Input(type="file", name="rfp_csv", accept=".csv"),
                Button("Upload RFP", type="submit"),
                hx_post="/upload_rfp",
                hx_target="#rfp-result",
                hx_swap="innerHTML",
                enctype="multipart/form-data",
            ),
            Div(id="rfp-result"),
            cls="section",
        ),
        Div(
            H2("3. Process RFP"),
            Button("Process RFP", id="process-rfp-btn"),
            Div(id="process-result"),
            cls="section",
        ),
        Div(
            Div(cls="progress-bar"),
            Div(id="progress-text"),
            cls="section",
        ),
        Script("""
            document.getElementById('process-rfp-btn').addEventListener('click', function() {
                var progressBar = document.querySelector('.progress-bar');
                var progressText = document.getElementById('progress-text');
                var processResult = document.getElementById('process-result');
                
                progressBar.innerHTML = '<div class="progress-bar-fill"></div>';
                progressText.textContent = '0 / 0 questions processed';
                processResult.textContent = '';
                
                var eventSource = new EventSource('/process_rfp');
                eventSource.onmessage = function(event) {
                    var data = JSON.parse(event.data);
                    if (data.progress) {
                        var progress = data.progress;
                        var percentage = (progress.current / progress.total) * 100;
                        document.querySelector('.progress-bar-fill').style.width = percentage + '%';
                        progressText.textContent = progress.current + ' / ' + progress.total + ' questions processed';
                    } else if (data.complete) {
                        eventSource.close();
                        processResult.innerHTML = 'RFP processing complete. <button onclick="window.location.href=\'/download?file=' + data.file + '\'">Download Results</button>';
                    }
                };
            });
        """),
        cls="container",
    )


@app.post("/upload_docs")
async def upload_docs(company_docs: list[UploadFile] = File(...)):
    global table_descriptions
    data_paths = []
    with tempfile.TemporaryDirectory() as temp_dir:
        for doc in company_docs:
            temp_file_path = Path(temp_dir) / doc.filename  # type: ignore
            content = await doc.read()
            with open(temp_file_path, "wb") as buffer:
                buffer.write(content)
            data_paths.append(temp_file_path)

        table_descriptions = add_data_with_descriptions(
            model=MODEL,
            lance_db=lance_db,
            data=data_paths,
            table_descriptions=table_descriptions,
        )

    return Div(
        f"Uploaded and processed {len(data_paths)} documents.", cls="alert alert-success"
    )


@app.post("/upload_rfp")
async def upload_rfp(rfp_csv: UploadFile = File(...)):
    global rfp_data
    content = await rfp_csv.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    rfp_data = pd.read_csv(temp_file_path)
    questions = rfp_data.iloc[:, 0].tolist()

    return Div(f"Uploaded RFP with {len(questions)} questions.", cls="alert alert-success")


@app.post("/process_rfp")
async def process_rfp():
    global progress
    if rfp_data is None:
        return Div("Please upload an RFP CSV file first.", cls="alert alert-danger")

    questions = rfp_data.iloc[:, 0].tolist()[-2:]
    progress["total"] = len(questions)
    progress["current"] = 0

    qna = {"questions": questions, "answers": [], "sources": []}

    app = application(db=lance_db, reranker=None, model=MODEL, has_web=False, only_data=True)

    async def generate():
        for query in questions:
            inputs = {"query": query}
            while True:
                step_result = app.step(inputs=inputs)
                if step_result is None:
                    break
                action, result, _ = step_result
                if action.name == "terminate":
                    break
                elif action.name in ["update_chat_history"]:
                    qna["answers"].append(result["chat_history"][-1]["content"].split("\n"))
                    qna["sources"].append(
                        [
                            {k: v for k, v in json.loads(d).items() if k != "index"}
                            for d in set(
                                [
                                    json.dumps(s, sort_keys=True)
                                    for s in app.state.get("source_docs", [])
                                ]
                            )
                        ]
                    )
                    progress["current"] += 1
                    yield f"data: {json.dumps({'progress': progress})}\n\n"
                    break

        # Generate Word document
        doc = Document()
        for q, a, s in zip(qna["questions"], qna["answers"], qna["sources"]):
            doc.add_heading(q, level=1)
            doc.add_paragraph("\n".join(a))
            doc.add_heading("Sources:", level=2)
            for source in s:
                doc.add_paragraph(f"- {source['text']} (From: {source['source']})")
            doc.add_page_break()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_file:
            doc.save(temp_file.name)

        yield f"data: {json.dumps({'complete': True, 'file': temp_file.name})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/download")
async def download(file: str):
    return FileResponse(file, filename="rfp_results.docx")


serve()
