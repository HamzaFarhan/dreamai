import json
from pathlib import Path

from instructor.client import T
from loguru import logger
from markdown2 import markdown
from pydantic import BaseModel, ValidationInfo, field_validator

from dreamai.ai import ModelName
from dreamai.dialog import Dialog, user_message
from dreamai.md_utils import MarkdownChunk, MarkdownData, data_to_md
from dreamai.utils import insert_xml_tag, to_snake
from loan_models import DealMain

MODEL = ModelName.GEMINI_FLASH
CHUNKS_LIMIT = 1.0
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
MIN_CHUNK_SIZE = 100


DATA_FILE = "hp.md"
DATA_JSON = "hp.json"
DATA_HTML = "hp_marked.html"
RES_JSON = "hp_res.json"

TASK = "You are a world-class AI financial advisor. Your task is to provide a detailed analysis of a loan application and extract the entities that I want. With sources if you can."


class ShortlistChunk(BaseModel):
    index: int
    context: str

    def __hash__(self):
        return hash(self.index)

    def __eq__(self, other):
        if isinstance(other, ShortlistChunk):
            return self.index == other.index
        return False


class Shortlist(BaseModel):
    chunks: list[ShortlistChunk]

    @field_validator("chunks")
    @classmethod
    def validate_indexes(
        cls, chunks: list[ShortlistChunk], info: ValidationInfo
    ) -> list[ShortlistChunk]:
        chunks = list(set(chunks))
        context = info.context
        if context is None:
            return chunks
        context_indexes = context.get("indexes", [])
        if not context_indexes:
            return chunks
        min_context_index = min(context_indexes)
        max_context_index = max(context_indexes)
        new_chunks = set()
        for chunk in chunks:
            if chunk.index in context_indexes:
                new_chunks.add(chunk)
            if chunk.index > min_context_index:
                prev_index = chunk.index - 1
                if prev_index in context_indexes:
                    new_chunks.add(ShortlistChunk(index=prev_index, context=chunk.context))
            if chunk.index < max_context_index:
                next_index = chunk.index + 1
                if next_index in context_indexes:
                    new_chunks.add(ShortlistChunk(index=next_index, context=chunk.context))
        return list(sorted(new_chunks, key=lambda x: x.index))


class RetrievedChunk(MarkdownChunk):
    context: str


if not Path(DATA_JSON).exists():
    data = data_to_md(
        data=DATA_FILE,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        min_chunk_size=MIN_CHUNK_SIZE,
    )[0]
    with open(DATA_JSON, "w") as f:
        json.dump(data.model_dump(), f, indent=2)  # type: ignore
else:
    with open(DATA_JSON, "r") as f:
        data = MarkdownData(**json.load(f))

# prompt_chunks = {
#     chunk.index: chunk.model_dump(exclude={"metadata"})
#     for chunk in data.chunks[: int(len(data.chunks) * CHUNKS_LIMIT)]
# }


def make_shortlist(user: str, chunks: list[dict], model: ModelName = MODEL):
    indexes = [chunk["index"] for chunk in chunks]
    dialog = Dialog(
        task=TASK,
        chat_history=[
            user_message(json.dumps(chunks)),
            user_message(
                "You have a list of chunks that make up the whole document. Each chunk has an index and may have some overlap with other chunks. Please give me the indexes of the chunks that have the relevant information. For each chunk, also give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk."
            ),
        ],
    )
    creator, kwargs = dialog.creator_with_kwargs(model=model, user=user)
    res = creator.create(
        **kwargs,
        response_model=Shortlist,
        validation_context={"indexes": indexes},
    )
    return res


def extract(
    user: str,
    chunks: list[dict],
    name: str = "",
    response_model: type[T] = str,
    model: ModelName = MODEL,
    res_json: str = RES_JSON,
):
    dialog = Dialog(task=TASK, chat_history=[user_message(json.dumps(chunks))])
    creator, kwargs = dialog.creator_with_kwargs(model=model, user=user)
    res = creator.create(**kwargs, response_model=response_model)
    if isinstance(res, list):
        dumped_res = [r.model_dump() for r in res]  # type: ignore
    else:
        dumped_res = res.model_dump()  # type: ignore
    name = name or to_snake(response_model.__name__)
    res_so_far = {}
    if Path(res_json).exists():
        try:
            with open(res_json, "r") as f:
                res_so_far = json.load(f)
        except Exception as e:
            logger.warning(f"Error loading {res_json}: {e}")
    res_so_far[name] = dumped_res
    with open(res_json, "w") as f:
        json.dump(res_so_far, f, indent=2)
    return res


response_model = DealMain

logger.info("Shortlisting chunks...")
with_metadata_chunks = {}
no_metadata_chunks = {}
for chunk in data.chunks:
    with_metadata_chunks[chunk.index] = chunk
    no_metadata_chunks[chunk.index] = chunk.model_dump(exclude={"metadata"})
shortlist = make_shortlist(
    user=response_model.shortlist_prompt(), chunks=list(no_metadata_chunks.values())
)
logger.success([chunk.index for chunk in shortlist.chunks])  # type: ignore
logger.info("Highlighting chunks...")
retrieved_chunks = []
for chunk in shortlist.chunks:  # type: ignore
    retrieved_chunks.append(
        RetrievedChunk(**no_metadata_chunks[chunk.index], context=chunk.context).model_dump()
    )
    with_metadata_chunk = with_metadata_chunks[chunk.index]
    start = with_metadata_chunk.metadata["start"]
    end = with_metadata_chunk.metadata["end"]
    logger.info(f"start: {start}, end: {end}")
    logger.warning(f"START: {data.markdown[start:start+10]}, END: {data.markdown[end-10:end]}")
    data.markdown = insert_xml_tag(text=data.markdown, tag="mark", start=start, end=end)
    marked_html = markdown(data.markdown)
    Path(DATA_HTML).write_text(marked_html.replace("\n", "<br>"))
logger.info("Extracting...")
res = extract(
    user=response_model.prompt(),
    chunks=retrieved_chunks,
    response_model=response_model,
    model=ModelName.GPT_MINI,
)
logger.success(res)


