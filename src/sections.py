import re

from src.model import build_tfidf
from src.preprocessing import clean_text, split_sentences

# Heading words for each section (matched on a line by itself, e.g. "3. Methods")
HEADINGS = {
    "abstract": r"abstract",
    "introduction": r"introduction",
    "methods": r"methods?|methodology|materials and methods|proposed method|approach",
    "results": r"results?|results and discussion|experiments?|evaluation|discussion",
    "conclusion": r"conclusions?|concluding remarks|conclusions and future work|summary",
    "references": r"references|bibliography",
}
MAX_SECTION_CHARS = 20000


def detect_sections(raw):
    """Find section headings in the RAW pdf text (before cleaning) and cut the text between them."""
    found = []
    for name, pattern in HEADINGS.items():
        rx = re.compile(rf"^\s*(?:\d+\.?\s+|[IVX]+\.\s+)?(?:{pattern})\s*:?\s*$", re.I | re.M)
        matches = list(rx.finditer(raw))
        if matches:
            m = matches[-1] if name == "references" else matches[0]   # last 'References', first of others
            found.append((m.start(), m.end(), name))
    found.sort()
    sections = {}
    for i, (_, end, name) in enumerate(found):
        stop = found[i + 1][0] if i + 1 < len(found) else len(raw)
        if name != "references":                       # references only marks where a section ends
            sections[name] = raw[end:stop].strip()[:MAX_SECTION_CHARS]
    return sections


def summarize_section(text, n=2):
    """Pick the n sentences with the highest average TF-IDF weight, in paper order."""
    sents = split_sentences(clean_text(text))
    if len(sents) <= n:
        return " ".join(sents)
    matrix = build_tfidf(sents)
    sums, counts = matrix.sum(axis=1).A1, matrix.getnnz(axis=1)
    scores = [s / c if c >= 4 else 0 for s, c in zip(sums, counts)]
    best = sorted(sorted(range(len(sents)), key=lambda i: scores[i], reverse=True)[:n])
    return " ".join(sents[i] for i in best)


def section_summaries(sections):
    """{section name: short summary} for every section that was found."""
    return {name: summarize_section(text) for name, text in sections.items() if text}