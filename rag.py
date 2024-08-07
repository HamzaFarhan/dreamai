from pathlib import Path
from typing import Annotated, Type

import lancedb
import pandas as pd
from lancedb.db import DBConnection
from lancedb.embeddings import SentenceTransformerEmbeddings, get_registry
from lancedb.pydantic import LanceModel
from lancedb.pydantic import Vector as LanceVector
from lancedb.table import Table as LanceTable
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import LanceDB
from langchain_core.documents import Document as LCDocument
from pydantic import AfterValidator, BaseModel, Field, create_model

from dreamai.ai import ModelName, create
