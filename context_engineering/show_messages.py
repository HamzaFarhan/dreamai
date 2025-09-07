from pathlib import Path

from pydantic_ai.messages import ModelMessagesTypeAdapter

MODULE_DIR = Path(__file__).parent

message_history_path = MODULE_DIR.joinpath("message_history.json")

messages = ModelMessagesTypeAdapter.validate_json(message_history_path.read_bytes())

messages