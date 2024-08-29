import shutil
from pathlib import Path

import lancedb
from lancedb.rerankers import ColbertReranker

from dreamai.ai import ModelName
from dreamai.rag import application
from dreamai.rag_utils import add_data_with_descriptions
from dreamai.settings import CreatorSettings, RAGAppSettings, RAGSettings

creator_settings = CreatorSettings()
rag_settings = RAGSettings()
rag_app_settings = RAGAppSettings()

MODEL = creator_settings.model
LANCE_URI = rag_settings.lance_uri
RERANKER = rag_settings.reranker
HAS_WEB = rag_app_settings.has_web
DATA = "/media/hamza/data2/RFP/docs"

if Path(LANCE_URI).exists():
    shutil.rmtree(LANCE_URI)
lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker(RERANKER)

table_descriptions = add_data_with_descriptions(
    model=ModelName.GEMINI_FLASH, lance_db=lance_db, data=DATA
)
print(f"\n\nTABLE DESCRIPTIONS\n\n{table_descriptions}\n\n")
app = application(
    db=lance_db,
    reranker=reranker,
    model=MODEL,
    table_descriptions=table_descriptions,
    has_web=HAS_WEB,
)
app.visualize(
    output_file_path="statemachine", include_conditions=True, include_state=False, format="png"
)


def main():
    queries = [
        "What is the main topic of the document?",
        "Can you summarize the key points?",
        "Are there any specific requirements mentioned?",
        "What is the deadline for submission?",
        "Who is the target audience for this document?",
    ]

    for query in queries:
        inputs = {"query": query}
        print(f"\nProcessing query: {query}")
        while True:
            step_result = app.step(inputs=inputs)
            if step_result is None:
                print("Error: app.step() returned None")
                break
            action, result, _ = step_result
            print(f"\nRESULT: {result}\n")
            if action.name == "terminate":
                break
            elif action.name in ["update_chat_history"]:
                break  # Move to the next query instead of getting user input


if __name__ == "__main__":
    main()
