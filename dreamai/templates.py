import os
from pathlib import Path

from .utils import deindent


def _txt_to_content(content_file: str | Path) -> str:
    if not os.path.exists(content_file := str(content_file)):
        return ""
    with open(content_file, "r") as f:
        content = f.read()
    return deindent(content)


def _process_content(content: str | Path | list[str]) -> str:
    if not content:
        return ""
    if isinstance(content, list):
        content = "\n\n---\n\n".join(list(content))
    elif isinstance(content, (Path, str)):
        content = str(content)
        if content.endswith(".txt"):
            content = _txt_to_content(content)
    return deindent(str(content))


def dict_to_markdown(
    content_dict: dict[str, str | Path | list[str]] | None = None,
    prefix: str = "",
    suffix: str = "",
) -> str:
    content_dict = content_dict or {}
    prompt = deindent(prefix).strip()
    for header, content in content_dict.items():
        if content:
            header = " ".join(header.split("_")).strip().title()
            content = _process_content(content).strip()
            if content:
                if prompt:
                    prompt += "\n\n"
                prompt += f"## {header}\n\n{content}"
    if suffix:
        prompt += "\n\n" + deindent(suffix).strip()
    return prompt.strip()
