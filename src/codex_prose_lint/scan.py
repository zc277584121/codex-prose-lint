"""Markdown-aware clause candidates with unchanged source offsets."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from markdown_it import MarkdownIt

# Cues nominate reference suggestions; Codex reviews the entire answer.
CUES = (
    r"不能|无法|并不|不是|不代表|不意味着|不等于|不一定|未必|不保证|不能保证|无法保证",
    r"不构成|仅供参考|仅限于|这只是|这仅是|这仅仅是|只是说明|只能说明|不能据此|无法据此|不应据此",
    r"需要注意|值得注意|需要指出|需要强调|需要说明|有必要说明|必须说明|严格来说",
    r"准确地说|更准确地说|从严格意义|在严格意义|理论上|原则上|某种程度上",
    r"并非绝对|并不绝对|并非所有|不适用于|具体情况|因人而异|因情况而异",
    r"以实际为准|以官方为准|自行核实|谨慎看待|保持谨慎|不做承诺|不作承诺",
    r"不承担|不负责任|不负任何|不提供.*保证|没有直接|尚未.*验证|还没有.*核实",
    r"不是.{0,30}而是|不只是|不仅仅是|不仅是|并不是|这并非|这不意味着",
    r"不会|做不到|办不到|达不到|不支持|不具备|不见得|不等同于",
    r"不足以|难以(?:保证|确保|确认|判断|确定)",
    r"没有|并未|尚未|还未|未曾|未能|未经|未见",
    r"未(?:做|作|检查|包含|涵盖|涉及|覆盖|验证|核实|确认|测试)",
    r"避免|以免|以防|防止|免得|不要|请勿|切勿|不应|不宜|不可",
    r"仅(?:作|用于|涉及)|只(?:涉及|针对|讨论)|暂不(?:涉及|讨论|涵盖)",
    r"不(?:包括|涵盖|涉及|包含)|不确保|不承诺|不予承诺",
    r"不[作做](?:任何|明确|额外|绝对|任何形式的)?(?:保证|背书)",
    r"(?:有待|尚待)(?:进一步)?(?:验证|确认|核实)|仍需(?:进一步)?(?:核实|验证|确认)",
    r"仍有可能|不排除|视情况而定",
    r"\b(?:cannot|can['’]t|unable\s+to|not\s+necessarily|does\s+not\s+(?:mean|imply|guarantee))\b",
    r"\b(?:do\s+not\s+(?:guarantee|assume)|no\s+guarantee|not\s+a\s+guarantee|may\s+not)\b",
    r"\b(?:important\s+to\s+note|worth\s+noting|keep\s+in\s+mind|to\s+be\s+clear)\b",
    r"\b(?:for\s+informational\s+purposes|not\s+(?:legal|medical|financial)\s+advice)\b",
    r"\b(?:strictly\s+speaking|in\s+principle|results\s+may\s+vary|not\s+responsible)\b",
    r"\b(?:not\s+intended\s+to|should\s+not\s+be\s+(?:taken|construed)|doesn['’]t\s+mean)\b",
)
CUE_RE = re.compile("|".join(f"(?:{cue})" for cue in CUES), re.IGNORECASE)
SOFT_END = set("，,；;：:")
HARD_END = set("。！？!?\n")


@dataclass(frozen=True)
class Candidate:
    id: str
    start: int
    end: int
    text: str
    sentence: str
    paragraph: str
    cues: tuple[str, ...]

    def context(self, mode: str) -> str:
        return self.text if mode == "clause" else getattr(self, mode)

    def to_dict(self) -> dict:
        return asdict(self)


def protected_mask(text: str) -> list[bool]:
    mask = [False] * len(text)

    def protect(start: int, end: int) -> None:
        mask[start:end] = [True] * (end - start)

    line_starts = [0]
    line_starts.extend(match.end() for match in re.finditer("\n", text))
    line_starts.append(len(text))
    for token in MarkdownIt("commonmark").enable("table").parse(text):
        if token.map and token.type in {"fence", "code_block", "html_block", "blockquote_open", "table_open"}:
            protect(line_starts[token.map[0]], line_starts[token.map[1]])

    # Match equal-length code delimiters without treating their contents as prose.
    pos = 0
    while pos < len(text):
        if text[pos] != "`" or mask[pos] or (pos and text[pos - 1] == "\\"):
            pos += 1
            continue
        run = re.match(r"`+", text[pos:]).group()
        closing = re.search(r"(?<!`)" + re.escape(run) + r"(?!`)", text[pos + len(run):])
        if closing:
            end = pos + len(run) + closing.end()
            protect(pos, end)
            pos = end
        else:
            pos += len(run)

    patterns = (
        r"~~[^\n]*?~~",                         # Existing annotations.
        r"!?\[[^\]\n]*\]\([^\n]*?\)",       # Inline links and images.
        r"!?\[[^\]\n]*\]\[[^\]\n]*\]",    # Reference links.
        r"https?://[^\s<>]+",                  # Bare URLs.
        r"<[^>\n]+>",                         # Inline HTML and autolinks.
        r"(?m)^\s*\[[^\]\n]+\]:[^\n]*",   # Reference definitions.
        r"(?m)^[ \t]*(?:#{1,6}[ \t]+|[-+*][ \t]+|\d+[.)][ \t]+)",
        r"(?<!\\)[*_]+",                      # Keep annotations inside emphasis boundaries.
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            protect(*match.span())
    return mask


def is_boundary(text: str, index: int, *, soft: bool) -> bool:
    char = text[index]
    if char in HARD_END:
        return True
    if char in (SOFT_END if soft else set()):
        return not (0 < index < len(text) - 1 and text[index - 1].isdigit() and text[index + 1].isdigit())
    if char == ".":
        # A single rule preserves decimal points, versions, filenames, and abbreviations.
        if index and text[index - 1].isdigit() and index + 1 < len(text) and text[index + 1].isdigit():
            return False
        word = re.search(r"[A-Za-z.]+$", text[:index])
        if word and (len(word.group()) == 1 or word.group().lower() in {"mr", "mrs", "ms", "dr", "prof", "e.g", "i.e", "vs"}):
            return False
        return index + 1 == len(text) or text[index + 1].isspace() or text[index + 1] in '"”」』'
    return False


def clipped_context(text: str, start: int, end: int, limit: int) -> str:
    if len(text) <= limit:
        return text.strip()
    center = (start + end) // 2
    left = max(0, min(center - limit // 2, len(text) - limit))
    return text[left:left + limit].strip()


def scan(text: str, *, context_limit: int = 2400) -> list[Candidate]:
    mask = protected_mask(text)
    sentence_edges = [0]
    for i in range(len(text)):
        if not mask[i] and is_boundary(text, i, soft=False):
            sentence_edges.append(i + 1)
    sentence_edges.append(len(text))
    paragraph_edges = [0, *(m.end() for m in re.finditer(r"\n[ \t]*\n", text)), len(text)]

    def context(edges: list[int], start: int, end: int) -> str:
        left = max(edge for edge in edges if edge <= start)
        right = next((edge for edge in edges if edge >= end), len(text))
        return clipped_context(text[left:right], start - left, end - left, context_limit)

    candidates = []
    start = 0

    def add(end: int) -> None:
        nonlocal start
        raw = text[start:end]
        left = start + len(raw) - len(raw.lstrip())
        right = end - (len(raw) - len(raw.rstrip()))
        if left < right:
            value = text[left:right]
            cues = tuple(dict.fromkeys(match.group() for match in CUE_RE.finditer(value)))
            if cues:
                candidates.append(Candidate(
                    f"c{len(candidates):03d}", left, right, value,
                    context(sentence_edges, left, right),
                    context(paragraph_edges, left, right), cues,
                ))
        start = end

    for i in range(len(text)):
        if mask[i]:
            add(i)
            start = i + 1
        elif is_boundary(text, i, soft=True):
            add(i)
            start = i + 1
    add(len(text))
    return candidates


def annotate(text: str, candidates: list[Candidate]) -> str:
    """Insert markup only; never rewrite or search-replace the source text."""
    previous = len(text)
    for candidate in sorted(candidates, key=lambda item: item.start, reverse=True):
        if not 0 <= candidate.start < candidate.end <= previous:
            raise ValueError("Overlapping or invalid annotation spans")
        if text[candidate.start:candidate.end] != candidate.text:
            raise ValueError("Annotation span no longer matches the source")
        text = text[:candidate.start] + "~~" + candidate.text + "~~" + text[candidate.end:]
        previous = candidate.start
    return text
