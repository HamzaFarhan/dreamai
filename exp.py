# %%

import json
import re
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

from dreamai.md_utils import MarkdownData, data_to_md
from dreamai.utils import insert_xml_tag
from gemini_exp import list_files

load_dotenv()

list_files()
# %%


def markdown_to_html(markdown):
    # Convert headers
    markdown = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", markdown, flags=re.MULTILINE)
    markdown = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", markdown, flags=re.MULTILINE)
    markdown = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", markdown, flags=re.MULTILINE)

    # Convert bold
    markdown = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", markdown)

    # Convert italic
    markdown = re.sub(r"\*(.*?)\*", r"<em>\1</em>", markdown)

    # Convert links
    markdown = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', markdown)

    # Convert mark tags
    markdown = re.sub(r"==(.*?)==", r"<mark>\1</mark>", markdown)

    # Convert unordered lists
    markdown = re.sub(r"^\* (.*?)$", r"<li>\1</li>", markdown, flags=re.MULTILINE)
    markdown = "<ul>" + markdown + "</ul>"

    # Convert paragraphs
    markdown = re.sub(r"(?<!\n)\n(?!\n)", r"<br>", markdown)
    markdown = re.sub(r"(?<!\n)\n\n(?!\n)", r"</p><p>", markdown)
    markdown = "<p>" + markdown + "</p>"

    return markdown


file_path = "/media/hamza/data2/loan2.pdf"
data_path = "pdf_md.json"
if not Path(data_path).exists():
    pdf_md = data_to_md(data=file_path, chunk_size=800, chunk_overlap=200)[0]
    with open(data_path, "w") as f:
        json.dump(pdf_md.model_dump(), f, indent=2)

# %%

file_path = "/media/hamza/data2/loan2.docx"
data_path = "docx_md.json"
if not Path(data_path).exists():
    docx_md = data_to_md(data=file_path, with_pages=False)[0]
    with open(data_path, "w") as f:
        json.dump(docx_md.model_dump(), f, indent=2)
# %%


# %%

pdf_md = MarkdownData(**json.loads(Path("pdf_md.json").read_text()))
chunk = pdf_md.chunks[14]
logger.info(chunk.text)
start = chunk.metadata["start"]
end = chunk.metadata["end"]
logger.info(f"start: {start}, end: {end}")
# logger.info(pdf_md.markdown[start:end])
marked_md = insert_xml_tag(text=pdf_md.markdown, tag="mark", start=start, end=end)
# marked_html = markdown(marked_md)
marked_html = markdown_to_html(marked_md)
Path("marked_html.html").write_text(marked_html.replace("\n", "<br>"))


# %%
data = "https://www.sec.gov/Archives/edgar/data/1645590/000164559024000119/ex-1039xcreditagreementame.htm"
data_md = data_to_md(data=data, chunk_size=800, chunk_overlap=200)[0]
Path("hp.md").write_text(data_md.markdown)


print(
    len("""The pricing grid is usually the information of the interest applicable to the borrower. The interest rate applicable is tied to the financial covenants ratio. If the ratio level is maintained according to the table of the pricing grid then the applicable interest rate will be different.

""")
)
