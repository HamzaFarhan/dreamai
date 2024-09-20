# %%
import concurrent.futures
import json
import re

from fuzzysearch import find_near_matches


def count_markdown_formatters(text: str) -> tuple[dict, int]:
    formatters = {
        "headers": (r"^#{1,6}\s", lambda m: len(m.strip())),
        "bold_italic": (r"\*{3}.*?\*{3}", lambda _: 6),
        "bold": (r"\*{2}.*?\*{2}", lambda _: 4),
        "italic": (r"\*.*?\*", lambda _: 2),
        "strikethrough": (r"~~.*?~~", lambda _: 4),
        "code_block": (r"```[\s\S]*?```", lambda _: 6),
        "inline_code": (r"`[^`\n]+`", lambda _: 2),
        "blockquote": (r"^>\s", lambda m: len(m.strip())),
        "unordered_list": (r"^\s*[-*+]\s", lambda m: len(m.strip())),
        "ordered_list": (r"^\s*\d+\.\s", lambda m: len(m.strip())),
        "horizontal_rule": (r"^---|\*\*\*|___\s*$", lambda m: len(m.strip())),
        "link": (r"\[.*?\]\(.*?\)", len),
        "image": (r"!\[.*?\]\(.*?\)", len),
    }
    counts = {f: len(re.findall(p, text, re.MULTILINE)) for f, (p, _) in formatters.items()}
    total = sum(
        sum(c(m) for m in re.findall(p, text, re.MULTILINE))
        for _, (p, c) in formatters.items()
    )
    return counts, total


all_md = json.load(open("md_chunks.json"))
page = 9
md_chunk = [chunk for chunk in all_md if chunk["metadata"]["page"] == page][0]
md = """
**Applicable Margin**" shall mean 0% with respect to the portion of the Loan to which a # Base Rate
Option applies, and *1.05%* with respect to the portion of the Loan to which a Term *SOFR* Rate Option applies.
"""

# %%
max_deletions = count_markdown_formatters(md)
print(max_deletions)


# %%


def find(subsequence: str, sequence: str, max_l_dist: int) -> list:
    return find_near_matches(subsequence, sequence, max_l_dist=max_l_dist)


def search_with_timeout(
    subsequence: str, sequence: str, max_l_dist: int, timeout: int = 30
) -> str:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(find, subsequence, sequence, max_l_dist=max_l_dist)
        try:
            matches = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"Search operation timed out after {timeout} seconds.")
            matches = []
    if not matches:
        return sequence
    return sequence[matches[0].start : matches[0].end]


# Use the function
try:
    match = search_with_timeout(
        subsequence=md, sequence=md_chunk["text"], max_l_dist=max_deletions[1] + 5, timeout=30
    )
except Exception as e:
    print(f"An error occurred: {e}")
    match = [md_chunk["text"]]  # Return the full sequence in case of any error


match
