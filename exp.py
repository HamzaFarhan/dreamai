# %%

import json
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger
from markdown2 import markdown

from dreamai.md_utils import MarkdownData, data_to_md
from dreamai.utils import insert_xml_tag

load_dotenv()
# %%

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
logger.info(pdf_md.markdown[start:end])
marked_md = insert_xml_tag(text=pdf_md.markdown, tag="mark", start=start, end=end)
Path("marked_html.html").write_text(markdown(marked_md.replace("\n", "<br>")))

# %
