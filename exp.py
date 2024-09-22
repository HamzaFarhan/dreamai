# %%

import json
from pathlib import Path

import markdown2
from dotenv import load_dotenv

from dreamai.md_utils import data_to_md
from dreamai.utils import insert_xml_tag

load_dotenv()
# %%

file_path = "/media/hamza/data2/loan2.pdf"
pdf_md = data_to_md(data=file_path, chunk_size=800, chunk_overlap=200)[0]
with open("pdf_md.json", "w") as f:
    json.dump(pdf_md.model_dump(), f, indent=2)

# %%

file_path = "/media/hamza/data2/loan2.docx"
docx_md = data_to_md(data=file_path, with_pages=False)[0]
with open("docx_md.json", "w") as f:
    json.dump(docx_md.model_dump(), f, indent=2)
# %%
[len(chunk.text) for chunk in pdf_md.chunks]


# %%

chunk = pdf_md.chunks[14]
print(chunk)
marked_md = insert_xml_tag(
    pdf_md.markdown, "mark", chunk.metadata["start"], chunk.metadata["end"]
)
Path("marked_pdf_html.html").write_text(marked_md)

# %%

url = "https://www.sec.gov/Archives/edgar/data/1645590/000164559024000119/ex-1039xcreditagreementame.htm"
url_md = data_to_md(
    data=url, headers={"User-Agent": "Mozilla/5.0 (Company info@company.com)"}
)[0].markdown
Path("url_md.md").write_text(url_md)

# %%

url_md = Path("url_md.md").read_text()
url_md = insert_xml_tag(url_md, "mark", 15, 50)
url_html = markdown2.markdown(url_md)
Path("url_html.html").write_text(url_html)

# %%

pdf_md = Path("pdf_md.md").read_text()
start = pdf_md.find(
    "revolving and amortising loan and letter of credit facility for\n\nloans of up"
)
end = start + 111
marked_pdf_md = insert_xml_tag(pdf_md, "mark", start, end)
pdf_html = markdown2.markdown(marked_pdf_md)
Path("pdf_html.html").write_text(pdf_html)
