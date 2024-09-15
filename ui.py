import tempfile
from pathlib import Path
from time import sleep

import pandas as pd
from fasthtml.common import (
    H1,
    H3,
    H6,
    Container,
    Div,
    Form,
    Img,
    Input,
    Li,
    Ol,
    Option,
    P,
    Select,
    Style,
    Ul,
    fast_app,
    serve,
)
from loguru import logger

from dreamai.md_utils import docs_to_md

# LANCE_DIR = Path("/home/hamza/dev/lance")
LANCE_DIR = Path("/home/hamza/dev/empty_lance")

TABLES_LIST_LIMIT = 5

style = """
.ui-indicator{
    display: none;
}
.htmx-request .ui-indicator{
    display: inline;
    color: #007bff;  /* Blue color */
}
.htmx-request.ui-indicator{
    display: inline;
    color: #007bff;  /* Blue color */
}
"""

app = fast_app(live=True, hdrs=(Style(style),))[0]


def get_sorted_indexes(index_folder: str | Path = LANCE_DIR) -> list[str]:
    index_folder = Path(index_folder)
    if not index_folder.exists():
        return []
    return sorted(
        [dir.name for dir in index_folder.iterdir() if dir.is_dir()],
        key=lambda x: index_folder.joinpath(x).stat().st_mtime,
        reverse=True,
    )


def divider():
    return Div(
        style="border-top: 1px solid #e0e0e0; margin: 30px 0;",
    )


def document_input(hx_swap_oob: str = "false"):
    return Input(
        type="file",
        name="documents",
        multiple=True,
        accept=".pdf,.docx,.txt,.md",
        id="document-input",
        hx_swap_oob=hx_swap_oob,
    )


def questionnaire_input(hx_swap_oob: str = "false"):
    return Input(
        type="file",
        name="questionnaire",
        accept=".csv",
        id="questionnaire-input",
        hx_swap_oob=hx_swap_oob,
    )


@app.get("/")
async def home(index: str = ""):
    indexes = get_sorted_indexes()
    current_index = index or indexes[0] if indexes else index
    container_elements = [
        H1("Business Questionnaire Tool"),
        divider(),
        Div(
            Select(
                *[
                    Option(index, value=index, selected=index == current_index)
                    for index in indexes
                ],
                name="index",
                id="index-select",
                hx_post="/select-index",
                hx_target="#index-info",
                hx_trigger="change, load",
            )
            if indexes
            else None,
            Input(
                type="text",
                name="index",
                placeholder="Create New Index",
                hx_post="/select-index",
                hx_target="#index-info",
                hx_trigger="keyup[key=='Enter']",
            ),
            id="index-controls",
        ),
        Div(id="index-info"),
        divider(),
        Div(
            H3("Upload Documents"),
            Form(
                document_input(),
                hx_post="/upload-documents",
                hx_trigger="change",
                hx_target="#documents-info",
                hx_indicator="#upload-indicator",
            ),
            Img(
                src="SVG-Loaders-master/svg-loaders/ball-triangle.svg",
                id="upload-indicator",
                cls="ui-indicator",
            ),
        ),
        Div(id="documents-info"),
        divider(),
        Div(
            H3("Upload your questionnaire CSV file"),
            Form(
                questionnaire_input(),
                hx_post="/upload-questionnaire",
                hx_trigger="change",
                hx_target="#questionnaire-info",
            ),
        ),
        Div(id="questionnaire-info"),
    ]

    return Container(*container_elements)


@app.get("/index-info")
def index_info(index: str, index_folder: str | Path = LANCE_DIR):
    index = index.strip().replace(" ", "_")
    existing_tables = get_sorted_indexes(Path(index_folder) / index)
    div = [H6(f"Selected/Created index: {index}")]
    if existing_tables:
        div.append(P(f"{len(existing_tables)} Existing tables:"))
        div.append(
            Ul(
                *[Li(table) for table in existing_tables],
                style="overflow-y: auto; max-height: 180px;",
            )
        )
    else:
        div.append(P("No tables found. Upload documents to create tables."))
    return Div(*div, id="index-info")


@app.post("/select-index")
def select_index(index: str = ""):
    return (
        index_info(index=index),
        document_input(hx_swap_oob="true"),
        Div(id="documents-info", hx_swap_oob="true"),
        questionnaire_input(hx_swap_oob="true"),
        Div(id="questionnaire-info", hx_swap_oob="true"),
    )


@app.post("/upload-documents")
async def upload_documents(request):
    form = await request.form()
    documents = form.getlist("documents")
    logger.info(documents)
    uploaded_files = []
    sleep(1)
    with tempfile.TemporaryDirectory() as temp_dir:
        for file in documents:
            logger.info(file)
            file_name = file.filename
            file_path = Path(temp_dir) / file_name
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            logger.success(f"{file_name} MD:\n\n{docs_to_md(file_path)[0].markdown}")
            uploaded_files.append(file_name)
        logger.info(f"Processed {len(uploaded_files)} files")

    return Div(
        H6(f"Uploaded {len(uploaded_files)} files"),
        Ul(*[Li(file) for file in uploaded_files]),
        hx_get="/index-info",
        hx_trigger="load",
        hx_target="#index-info",
        hx_include="#index-select",
    )


@app.post("/upload-questionnaire")
async def upload_questionnaire(request):
    form = await request.form()
    csv_file = form.get("questionnaire")

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / csv_file.filename
        with open(file_path, "wb") as f:
            f.write(csv_file.file.read())

        df = pd.read_csv(file_path)
        questions = df.iloc[:, 0].tolist()
        question_count = len(questions)

        logger.info(f"Uploaded CSV file: {csv_file.filename} with {question_count} questions")
        logger.info(f"Stored {question_count} questions in global variable")

    return Div(
        P(f"Questionnaire file '{csv_file.filename}' uploaded successfully."),
        P(f"Number of questions: {question_count}"),
        Ol(
            *[
                Li(question[:100] + "..." if len(question) > 100 else question)
                for question in questions
            ],
            style="overflow-y: auto; max-height: 250px;",
        ),
    )


if __name__ == "__main__":
    serve()
