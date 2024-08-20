import shutil
from pathlib import Path

import lancedb
from lancedb.rerankers import ColbertReranker

from rag_app import add_data, application, get_user_query

# Constants
LANCE_URI = "lance/rag/"
DATA_PATH = "rag_data"

# Remove existing database if it exists
if Path(LANCE_URI).exists():
    shutil.rmtree(LANCE_URI)

# Connect to the database and initialize reranker
lance_db = lancedb.connect(uri=LANCE_URI)
reranker = ColbertReranker("answerdotai/answerai-colbert-small-v1")

# Add data to the database
table_descriptions = add_data(lance_db=lance_db, data_path=DATA_PATH)

# Initialize the application
app = application(
    db=lance_db, reranker=reranker, table_descriptions=table_descriptions, has_web=True
)

# Visualize the application state machine
app.visualize(
    output_file_path="statemachine",
    include_conditions=True,
    include_state=False,
    format="png",
)


# Main interaction loop
def main():
    inputs = {"query": get_user_query()}
    while True:
        step_result = app.step(inputs=inputs)
        if step_result is None:
            print("Error: app.step() returned None")
            break
        action, result, state = step_result
        print(f"\nRESULT: {result}\n")
        if action.name == "terminate":
            break
        elif action.name in ["ask_assistant", "create_search_response"]:
            inputs["query"] = get_user_query()


if __name__ == "__main__":
    main()

# Uncomment the following line to print the chat history after the main loop
# print(app.state["chat_history"])
