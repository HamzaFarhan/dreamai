# %%

from datetime import timedelta
from pathlib import Path
from time import sleep

import google.generativeai as genai
import typer
from dotenv import load_dotenv
from google.generativeai import GenerationConfig, caching
from google.generativeai.types.file_types import File
from loguru import logger

from dreamai.ai import ModelName

load_dotenv()

# [model.name for model in genai.list_models()]


# %%

typer_app = typer.Typer()

MODEL = ModelName.GEMINI_PRO
SYSTEM = "As an expert data extractor, you will have to extract certain elements from this loan agreement form. Assume that all of the requested elements are defined in the document. If you think they are not, look harder. You must provide sources for each element."
GENERATION_CONFIG = {
    "temperature": 0.1,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "text/plain",
}


@typer_app.command()
def upload_file(path: str, name: str = "", mime_type=None) -> File:
    name = name or Path(path).stem
    file = genai.upload_file(path=path, mime_type=mime_type, name=name, display_name=name)
    logger.info(f"Uploaded file '{file.display_name}' as: {file.uri}")
    while file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        sleep(1)
        file = genai.get_file(file.name)
    logger.info(f"File '{file.display_name}' is ready: {file.uri}, {file.name}")
    return file


@typer_app.command()
def list_files():
    logger.info(list(genai.list_files()))


@typer_app.command()
def delete_file(name: str) -> None:
    genai.delete_file(name=name)


@typer_app.command()
def create_cache(
    file_name: str, model: ModelName = MODEL, system_instruction: str = SYSTEM, hours: int = 3
) -> caching.CachedContent:
    file = genai.get_file(file_name)
    cache = caching.CachedContent.create(
        model=model,
        display_name=file.display_name,
        system_instruction=system_instruction or None,
        contents=[file],
        ttl=timedelta(hours=hours),
    )
    logger.info(f"Created cache: {cache.name}")
    return cache


@typer_app.command()
def list_caches():
    logger.info(list(caching.CachedContent.list()))


@typer_app.command()
def delete_cache(name: str):
    caching.CachedContent.get(name=name).delete()


@typer_app.command()
def delete_caches():
    for cache in caching.CachedContent.list():
        cache.delete()


@typer_app.command()
def generate(
    prompt: str, file_name: str = "", cache_name: str = "", model_name: ModelName = MODEL
) -> str:
    assert file_name or cache_name, "Either file_name or cache_name must be provided"
    contents = [prompt]
    if file_name:
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=GenerationConfig(**GENERATION_CONFIG),
            system_instruction=SYSTEM,
        )
        contents.insert(0, genai.get_file(file_name))  # type: ignore
    else:
        model = genai.GenerativeModel.from_cached_content(
            cached_content=caching.CachedContent.get(name=cache_name),
            generation_config=GenerationConfig(**GENERATION_CONFIG),
        )
    res = model.generate_content(contents=contents).text
    logger.info(f"Generated content: {res}")
    return res


if __name__ == "__main__":
    typer_app()
