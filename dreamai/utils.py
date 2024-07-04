import inspect
import json
import quopri
import re
import textwrap
import traceback
import typing
from datetime import datetime
from functools import partial
from itertools import chain
from pathlib import Path
from typing import Callable, Final, Iterable

import demoji
from IPython.display import Markdown
from pydantic import create_model

UNICODE_BULLETS: Final[list[str]] = [
    "\u0095",
    "\u2022",
    "\u2023",
    "\u2043",
    "\u3164",
    "\u204c",
    "\u204d",
    "\u2219",
    "\u25cb",
    "\u25cf",
    "\u25d8",
    "\u25e6",
    "\u2619",
    "\u2765",
    "\u2767",
    "\u29be",
    "\u29bf",
    "\u002d",
    "",
    "\*",  # type: ignore
    "\x95",
    "·",
]
BULLETS_PATTERN = "|".join(UNICODE_BULLETS)
UNICODE_BULLETS_RE_0W = re.compile(f"(?={BULLETS_PATTERN})(?<!{BULLETS_PATTERN})")
UNICODE_BULLETS_RE = re.compile(f"(?:{BULLETS_PATTERN})(?!{BULLETS_PATTERN})")
E_BULLET_PATTERN = re.compile(r"^e(?=\s)", re.MULTILINE)
PARAGRAPH_PATTERN = r"\s*\n\s*"
PARAGRAPH_PATTERN_RE = re.compile(
    f"((?:{BULLETS_PATTERN})|{PARAGRAPH_PATTERN})(?!{BULLETS_PATTERN}|$)",
)
DOUBLE_PARAGRAPH_PATTERN_RE = re.compile("(" + PARAGRAPH_PATTERN + "){2}")


def run_code(code, *args, **kwargs):
    try:
        function_def = "def " + code.split("def ")[1].split("\n")[0]
        code_before, code_after = code.split(function_def)
        code = f"{function_def}\n{' '*4}{code_before.strip()}\n{code_after}"
        func = code.split("def ")[1].split("(")[0]
        exec(code)
        func = locals()[func]
        return func(*args, **kwargs)
    except Exception:
        return traceback.format_exc()


def function_schema(f: Callable) -> dict:
    kw = {
        n: (o.annotation, ... if o.default == inspect.Parameter.empty else o.default)
        for n, o in inspect.signature(f).parameters.items()
    }
    s = create_model(f"Input for `{f.__name__}`", **kw).schema()  # type: ignore
    return dict(name=f.__name__, description=f.__doc__, parameters=s)


def flatten(o: Iterable):
    "Concatenate all collections and items as a generator"
    for item in o:
        if isinstance(item, str):
            yield item
            continue
        try:
            yield from flatten(item)
        except TypeError:
            yield item


def extract_json(s):
    s = s[next(idx for idx, c in enumerate(s) if c in "{[") :]
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        return json.loads(s[: e.pos])


def noop(x=None, *args, **kwargs):
    return x


def resolve_data_path(data_path: list | str | Path) -> chain:
    if not isinstance(data_path, list):
        data_path = [data_path]
    paths = []
    for dp in flatten(data_path):
        if isinstance(dp, (str, Path)):
            dp = Path(dp)
            if not dp.exists():
                raise Exception(f"Path {dp} does not exist.")
            if dp.is_dir():
                paths.append(dp.iterdir())
            else:
                paths.append([dp])
    return chain(*paths)


def flatten_list(my_list: list) -> list:
    """Flatten a list of lists."""
    new_list = []
    for x in my_list:
        if isinstance(x, list):
            new_list += flatten_list(x)
        else:
            new_list.append(x)
    return new_list


def deindent(text: str) -> str:
    return textwrap.dedent(inspect.cleandoc(text))


def remove_digits(text: str) -> str:
    return re.sub(r"\d+", "", text)


def format_encoding_str(encoding: str) -> str:
    """Format input encoding string (e.g., `utf-8`, `iso-8859-1`, etc).
    Parameters
    ----------
    encoding
        The encoding string to be formatted (e.g., `UTF-8`, `utf_8`, `ISO-8859-1`, `iso_8859_1`,
        etc).
    """
    formatted_encoding = encoding.lower().replace("_", "-")

    # Special case for Arabic and Hebrew charsets with directional annotations
    annotated_encodings = [
        "iso-8859-6-i",
        "iso-8859-6-e",
        "iso-8859-8-i",
        "iso-8859-8-e",
    ]
    if formatted_encoding in annotated_encodings:
        formatted_encoding = formatted_encoding[:-2]  # remove the annotation

    return formatted_encoding


def bytes_string_to_string(text: str, encoding: str = "utf-8"):
    """Converts a string representation of a byte string to a regular string using the
    specified encoding."""
    text_bytes = bytes([ord(char) for char in text])
    formatted_encoding = format_encoding_str(encoding)
    return text_bytes.decode(formatted_encoding)


def clean_non_ascii_chars(text) -> str:
    """Cleans non-ascii characters from unicode string.

    Example
    -------
    \x88This text contains non-ascii characters!\x88
        -> This text contains non-ascii characters!
    """
    en = text.encode("ascii", "ignore")
    return en.decode()


def group_bullet_paragraph(paragraph: str) -> list:
    """Groups paragraphs with bullets that have line breaks for visual/formatting purposes.
    For example:

    '''○ The big red fox
    is walking down the lane.

    ○ At the end of the lane
    the fox met a friendly bear.'''

    Gets converted to

    '''○ The big red fox is walking down the lane.
    ○ At the end of the land the fox met a bear.'''
    """
    clean_paragraphs = []
    # pytesseract converts some bullet points to standalone "e" characters.
    # Substitute "e" with bullets since they are later used in partition_text
    # to determine list element type.
    paragraph = (re.sub(E_BULLET_PATTERN, "·", paragraph)).strip()

    bullet_paras = re.split(UNICODE_BULLETS_RE_0W, paragraph)
    for bullet in bullet_paras:
        if bullet:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", bullet))
    return clean_paragraphs


def group_broken_paragraphs(
    text: str,
    line_split: re.Pattern[str] = PARAGRAPH_PATTERN_RE,
    paragraph_split: re.Pattern[str] = DOUBLE_PARAGRAPH_PATTERN_RE,
) -> str:
    """Groups paragraphs that have line breaks for visual/formatting purposes.
    For example:

    '''The big red fox
    is walking down the lane.

    At the end of the lane
    the fox met a bear.'''

    Gets converted to

    '''The big red fox is walking down the lane.
    At the end of the land the fox met a bear.'''
    """
    paragraphs = paragraph_split.split(text)
    clean_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        # NOTE(robinson) - This block is to account for lines like the following that shouldn't be
        # grouped together, but aren't separated by a double line break.
        #     Apache License
        #     Version 2.0, January 2004
        #     http://www.apache.org/licenses/
        para_split = line_split.split(paragraph)
        all_lines_short = all(len(line.strip().split(" ")) < 5 for line in para_split)
        # pytesseract converts some bullet points to standalone "e" characters
        if UNICODE_BULLETS_RE.match(paragraph.strip()) or E_BULLET_PATTERN.match(
            paragraph.strip()
        ):
            clean_paragraphs.extend(group_bullet_paragraph(paragraph))
        elif all_lines_short:
            clean_paragraphs.extend([line for line in para_split if line.strip()])
        else:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", paragraph))

    return "\n\n".join(clean_paragraphs)


def replace_mime_encodings(text: str, encoding: str = "utf-8") -> str:
    """Replaces MIME encodings with their equivalent characters in the specified encoding.

    Example
    -------
    5 w=E2=80-99s -> 5 w’s
    """
    formatted_encoding = format_encoding_str(encoding)
    return quopri.decodestring(text.encode(formatted_encoding)).decode(
        formatted_encoding
    )


def replace_unicode_quotes(text: str) -> str:
    """Replaces unicode bullets in text with the expected character

    Example
    -------
    \x93What a lovely quote!\x94 -> “What a lovely quote!”
    """
    # NOTE(robinson) - We should probably make this something more sane like a regex
    # instead of a whole big series of replaces
    text = text.replace("\x91", "‘")
    text = text.replace("\x92", "’")
    text = text.replace("\x93", "“")
    text = text.replace("\x94", "”")
    text = text.replace("&apos;", "'")
    text = text.replace("â\x80\x99", "'")
    text = text.replace("â\x80“", "—")
    text = text.replace("â\x80”", "–")
    text = text.replace("â\x80˜", "‘")
    text = text.replace("â\x80¦", "…")
    text = text.replace("â\x80™", "’")
    text = text.replace("â\x80œ", "“")
    text = text.replace("â\x80?", "”")
    text = text.replace("â\x80ť", "”")
    text = text.replace("â\x80ś", "“")
    text = text.replace("â\x80¨", "—")
    text = text.replace("â\x80ł", "″")
    text = text.replace("â\x80Ž", "")
    text = text.replace("â\x80‚", "")
    text = text.replace("â\x80‰", "")
    text = text.replace("â\x80‹", "")
    text = text.replace("â\x80", "")
    text = text.replace("â\x80s'", "")
    return text


def clean_text(
    text: str, no_digits: bool = False, no_emojis: bool = False, group: bool = False
) -> str:
    text = re.sub(r"[\n+]", "\n", text)
    text = re.sub(r"[\t+]", " ", text)
    text = re.sub(r"[. .]", " ", text)
    text = re.sub(r"([ ]{2,})", " ", text)
    # print(text)
    try:
        text = bytes_string_to_string(text)
        # print(text)
    except Exception:
        pass
    try:
        text = clean_non_ascii_chars(text)
        # print(text)
    except Exception:
        pass
    try:
        text = replace_unicode_quotes(text)
        # print(text)
    except Exception:
        pass
    try:
        text = replace_mime_encodings(text)
        # print(text)
    except Exception:
        pass
    if group:
        try:
            text = "\n".join(group_bullet_paragraph(text))
            # print(text)
        except Exception:
            pass
        try:
            text = group_broken_paragraphs(text)
            # print(text)
        except Exception:
            pass
    if no_digits:
        text = remove_digits(text)
    if no_emojis:
        text = demoji.replace(text, "")
    return text.strip()


def get_param_names(func: Callable):
    func = func.func if type(func) == partial else func
    return inspect.signature(func).parameters.keys()


def get_required_param_names(func: Callable) -> list[str]:
    if type(func) == partial:
        params = inspect.signature(func.func).parameters
        return [
            name
            for name, param in params.items()
            if param.default == inspect.Parameter.empty
            and name not in func.keywords.keys()
        ]
    params = inspect.signature(func).parameters
    return [
        name
        for name, param in params.items()
        if param.default == inspect.Parameter.empty
    ]


def get_function_return_type(func: Callable) -> type:
    func = func.func if type(func) == partial else func
    sig = typing.get_type_hints(func)
    return sig.get("return", None)


def get_function_name(func: Callable) -> str:
    func = func.func if type(func) == partial else func
    return func.__name__


def get_function_source(func: Callable) -> str:
    func = func.func if type(func) == partial else func
    return inspect.getsource(func)


def get_function_info(func: Callable) -> str:
    """Get a string with the name, signature, and docstring of a function."""

    func = func.func if type(func) == partial else func
    name = func.__name__
    signature = inspect.signature(func)
    docstring = inspect.getdoc(func)
    desc = f"\n---\nA function:\nName: {name}\n"
    if signature:
        desc += f"Signature: {signature}\n"
    if docstring:
        desc += f"Docstring: {docstring}\n"
    return inspect.cleandoc(desc + "---\n\n")


def to_markdown(text: str) -> Markdown:
    return Markdown(
        textwrap.indent(text.replace("•", "  *"), "> ", predicate=lambda _: True)
    )


def current_time(format: str = "%m-%d-%Y_%H:%M:%S") -> str:
    # print(f"\n\nCURRENT TIME: {datetime.now().strftime(format)}\n\n")
    return datetime.now().strftime(format)


def sort_times(times, format="%m-%d-%Y_%H:%M:%S"):
    return sorted(times, key=lambda time: datetime.strptime(time, format))


def count_words(text: str) -> int:
    return len(text.split())


def count_lines(text: str) -> int:
    return len(text.split("\n"))


def token_count_to_word_count(token_count) -> int:
    return max(int(token_count * 0.75), 1)


def token_count_to_line_count(token_count) -> int:
    return max(int(token_count * 0.066), 1)


def word_count_to_token_count(word_count) -> int:
    return max(int(word_count / 0.75), 1)


def count_tokens(text: str) -> int:
    return word_count_to_token_count(len(text.split()))
