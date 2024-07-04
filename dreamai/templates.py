import os
from pathlib import Path

from .utils import deindent


def dict_to_xml(d: dict) -> str:
    xml_str = ""
    for key, value in d.items():
        xml_str += f"<{key}>\n{value}\n</{key}>\n"
    return xml_str.strip()


def txt_to_prompt(prompt_file: str | Path) -> str:
    if not os.path.exists(prompt_file := str(prompt_file)):
        return ""
    with open(prompt_file, "r") as f:
        prompt = f.read()
    return deindent(prompt)


def process_prompt(prompt: str | Path | list[str]) -> str:
    if not prompt:
        return ""
    if isinstance(prompt, list):
        prompt = "\n\n---\n\n".join(list(prompt))
    elif isinstance(prompt, (Path, str)):
        prompt = str(prompt)
        if prompt.endswith(".txt"):
            prompt = txt_to_prompt(prompt)
    return deindent(str(prompt))


def titles_w_content_template(
    titles_dict: dict[str, str | Path | list[str]] = {},
    prefix: str = "",
    suffix: str = "",
) -> str:
    prompt = deindent(prefix)
    for title, content in titles_dict.items():
        if content:
            title = " ".join(title.split("_")).strip().title()
            content = process_prompt(content)
            if content:
                if len(prompt) > 0:
                    prompt += "\n\n"
                prompt += deindent(f"## {title} ##\n\n{deindent(content)}")
    prompt += "\n\n" + deindent(suffix)
    return deindent(prompt)
