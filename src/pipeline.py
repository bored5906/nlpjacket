import time

from src.evaluation import evaluate_summary
from src.insights import extract_entities, extract_keywords, key_insights
from src.model import summarize
from src.preprocessing import clean_text, extract_text, preprocess_sentence, split_sentences
from .sections import detect_sections, section_summaries

MODES = {"fast", "accurate", "compare"}
LENGTHS = {"short", "medium", "long"}
NORMS = {"lemma", "stem"}


def run_pipeline(pdf_path, mode="accurate", length="medium", normalization="lemma", ngram="1-2"):
    """Run all stages on one PDF. Returns a dict shaped like app/static/mock.json."""
    if mode not in MODES or length not in LENGTHS or normalization not in NORMS:
        raise ValueError("Invalid option value.")
    trace = []

    def mark(stage, started, preview):
        trace.append({"stage": stage, "ms": int((time.perf_counter() - started) * 1000), "output_preview": preview})

    # 1. extract
    t = time.perf_counter()
    raw = extract_text(pdf_path)
    mark("PDF extraction", t, f"{len(raw):,} characters")
    if len(raw.strip()) < 500:
        raise ValueError("Almost no text found. The PDF may be scanned; use a text-based PDF.")

    # 2. sections, and take the abstract out so it can be the ROUGE reference
    t = time.perf_counter()
    sections = detect_sections(raw)
    abstract = sections.get("abstract", "")
    has_reference = 40 <= len(abstract.split()) <= 400
    body = raw.replace(abstract, "", 1) if has_reference else raw
    mark("Section detection", t, ", ".join(sections) or "no headings found")

    # 3. clean + sentences
    t = time.perf_counter()
    text = clean_text(body)
    sentences = split_sentences(text)
    mark("Cleaning and sentence split", t, f"{len(sentences)} sentences kept")
    if len(sentences) < 8:
        raise ValueError("Too little readable text to summarize.")

    # 4. preprocessing (shown for the trace; the summarizers repeat it internally)
    t = time.perf_counter()
    sample = preprocess_sentence(sentences[min(5, len(sentences) - 1)], normalization)
    mark(f"Preprocessing ({normalization})", t, ", ".join(sample[:8]))

    # 5. summaries
    t = time.perf_counter()
    summaries = summarize(sentences, mode, length, normalization)
    mark(f"Summarization ({mode})", t, ", ".join(f"{k}: {len(v.split())} words" for k, v in summaries.items()))

    # 6. keywords, entities, insights, section summaries
    t = time.perf_counter()
    keywords = extract_keywords(text, ngram)
    mark("Keywords (YAKE + POS filter)", t, ", ".join(k["term"] for k in keywords[:4]))
    t = time.perf_counter()
    entities = extract_entities(text)
    mark("Named entities (spaCy)", t, f"{sum(len(v) for v in entities.values())} entities")
    t = time.perf_counter()
    insights = key_insights(sentences)
    mark("Key insights (cue phrases)", t, f"{sum(1 for v in insights.values() if v)} of 4 found")
    t = time.perf_counter()
    section_text = section_summaries(sections)
    mark("Section summaries", t, f"{len(section_text)} sections")

    # 7. evaluation against the paper's own abstract
    evaluation = {}
    if has_reference:
        t = time.perf_counter()
        words = len(text.split())
        evaluation = {name: evaluate_summary(s, abstract, words) for name, s in summaries.items()}
        mark("ROUGE evaluation", t, f"scored {len(evaluation)} methods vs the abstract")

    return {
        "title": " ".join(k["term"] for k in keywords[:2]) or "untitled",
        "mode": mode,
        "length": length,
        "summaries": summaries,
        "insights": insights,
        "keywords": keywords,
        "entities": entities,
        "sections": section_text,
        "trace": trace,
        "evaluation": evaluation,
        "abstract_found": has_reference,
    }