import io

import pandas as pd
from fasthtml.common import (
    H1,
    Button,
    Container,
    Div,
    Form,
    Input,
    Table,
    Td,
    Th,
    Titled,
    Tr,
    fast_app,
    serve,
)
from loguru import logger

app = fast_app(live=True)[0]


@app.get("/")
async def index():
    upload_form = Form(
        Input(type="file", name="csv_file", accept=".csv"),
        Button("Upload", type="submit"),
        action="/upload",
        method="post",
        enctype="multipart/form-data",
    )
    return Titled(
        "CSV Uploader", Container(H1("CSV Uploader"), upload_form, Div(id="csv-content"))
    )


@app.post("/upload")
async def upload_csv(request):
    form = await request.form()
    csv_file = form.get("csv_file")

    if not csv_file:
        logger.error("No file was uploaded")
        return Div("No file was uploaded", id="csv-content")

    content = await csv_file.read()
    csv_content = io.BytesIO(content)

    try:
        df = pd.read_csv(csv_content)
    except pd.errors.EmptyDataError:
        logger.warning("CSV file is empty")
        return Div("CSV file is empty", id="csv-content")

    table = Table(
        Tr(*[Th(col) for col in df.columns]),
        *[Tr(*[Td(cell) for cell in row]) for row in df.values],
    )

    logger.info(f"Successfully processed CSV file: {csv_file.filename}")
    return Div(table, id="csv-content")


if __name__ == "__main__":
    logger.info("Starting CSV Uploader app")
    serve()
