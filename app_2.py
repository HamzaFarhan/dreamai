import shutil
from pathlib import Path

import lancedb
from lancedb.rerankers import ColbertReranker

from dreamai.rag_utils import get_user_query
from dreamai.search_actions import _add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGSettings
from rag_app_2 import application

creator_settings = CreatorSettings()
rag_settings = RAGSettings()

MODEL = creator_settings.model
LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
DATA_PATH = "rag_data"

if Path(LANCE_URI).exists():
    shutil.rmtree(LANCE_URI)
lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(RERANKER)

table_descriptions = _add_data_with_descriptions(
    model=MODEL, lance_db=lance_db, data_path=DATA_PATH
)
app = application(
    db=lance_db, reranker=reranker, model=MODEL, table_descriptions=table_descriptions
)
app.visualize(
    output_file_path="statemachine",
    include_conditions=True,
    include_state=False,
    format="png",
)


def main():
    inputs = {"query": get_user_query()}
    while True:
        step_result = app.step(inputs=inputs)
        if step_result is None:
            print("Error: app.step() returned None")
            break
        action, result, _ = step_result
        print(f"\nRESULT: {result}\n")
        if action.name == "terminate":
            break
        elif action.name in ["ask_assistant", "create_search_response"]:
            inputs["query"] = get_user_query()


if __name__ == "__main__":
    main()
