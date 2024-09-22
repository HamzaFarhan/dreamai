import concurrent.futures
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


def search_with_timeout(
    subsequence: str, sequence: str, max_l_dist: int, timeout: int = 30
) -> str:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(
            find_near_matches,
            subsequence=subsequence,
            sequence=sequence,
            max_l_dist=max_l_dist,
        )
        try:
            matches = future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"Search operation timed out after {timeout} seconds.")
            matches = []
    if not matches:
        return sequence
    return sequence[matches[0].start : matches[0].end]
