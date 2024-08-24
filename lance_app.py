import shutil
from pathlib import Path

import lancedb
from lancedb.rerankers import ColbertReranker

from dreamai.search_actions import add_data_with_descriptions
from dreamai.settings import RAGSettings, CreatorSettings

rag_settings = RAGSettings()
creator_settings = CreatorSettings()

MODEL = creator_settings.model
LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
TEXT_FIELD_NAME = rag_settings.text_field_name

DATA_PATH = "rag_data"

# Remove existing database if it exists
if Path(LANCE_URI).exists():
    shutil.rmtree(LANCE_URI)

# Connect to the database and initialize reranker
lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(model_name=RERANKER, column=TEXT_FIELD_NAME)

# Add data to the database
table_descriptions = add_data_with_descriptions(
    model=MODEL, lance_db=lance_db, data_path=DATA_PATH
)
