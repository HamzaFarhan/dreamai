from dataclasses import dataclass
from pathlib import Path

from dreamai.agent import AgentDeps


@dataclass(init=False)
class DataDirs:
    thread_dir: Path
    workspace_dir: Path
    analysis_dir: Path
    results_dir: Path
    data_dir: Path
    message_history_path: Path

    def __init__(self, thread_dir: Path, workspace_dir: Path):
        self.thread_dir = thread_dir.expanduser().resolve()
        self.workspace_dir = workspace_dir
        self.results_dir = self.thread_dir / "results"
        self.data_dir = self.workspace_dir / "data"
        self.message_history_path = self.thread_dir / "message_history.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)


class FinnDeps(AgentDeps):
    dirs: DataDirs
