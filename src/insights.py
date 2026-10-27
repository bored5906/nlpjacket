import re
from collections import Counter

import spacy
import yake

nlp = spacy.load("en_core_web_sm")
KEEP_ENTITIES = {"PERSON", "ORG", "GPE", "LOC", "NORP", "PRODUCT", "EVENT"}
BAD = re.compile(r"@xmath|\$|\[|\]|_|\+|\d{5,}")      # math placeholders and junk

CUES = {
    "objective":   ["we propose", "we present", "in this paper", "this paper", "we investigate", "we study", "aim", "goal"],
    "method":      ["we use", "we used", "we apply", "we employ", "based on", "method", "approach", "algorithm"],
    "findings":    ["results show", "we found", "we find", "shows that", "indicates", "demonstrate", "significant"],
    "limitations": ["limitation", "however", "future work", "cannot", "not able", "fail", "drawback"],
}
REGION = {"objective": (0.0, 0.25), "findings": (0.65, 1.0), "limitations": (0.65, 1.0)}


def extract_keywords(text, ngram="1-2", top=10):
    """YAKE finds keyphrases; a POS check keeps only phrases containing a noun."""
    n = int(ngram.split("-")[1])
    raw = yake.KeywordExtractor(lan="en", n=n, top=top * 3, dedupLim=0.7).extract_keywords(text)
    kept, seen = [], set()
    for term, score in raw:                            # YAKE: LOWER score = better phrase
        term = term.lower()
        if BAD.search(term) or term in seen:
            continue
        if not any(t.pos_ in ("NOUN", "PROPN") for t in nlp(term)):
            continue                                   # POS tagging filter
        seen.add(term)
        kept.append((term, score))
    kept = kept[:top]
    if not kept:
        return []
    best = min(s for _, s in kept) or 1e-6
    return [{"term": t, "score": round(best / s, 2)} for t, s in kept]   # best phrase = 1.0


def extract_entities(text, per_type=8, max_chars=100000):
    """spaCy NER, grouped by type, most frequent first."""
    doc = nlp(text[:max_chars])
    counts = {}
    for ent in doc.ents:
        if ent.label_ in KEEP_ENTITIES and not BAD.search(ent.text):
            counts.setdefault(ent.label_, Counter())[ent.text.strip()] += 1
    return {label: [e for e, _ in c.most_common(per_type)] for label, c in counts.items()}


def key_insights(sentences):
    """For each category, pick the sentence with the most cue phrases, favoring the right part of the paper."""
    total, result = len(sentences), {}
    for name, cues in CUES.items():
        best, best_score = "", 0
        for i, s in enumerate(sentences):
            low = s.lower()
            hits = sum(c in low for c in cues)
            if hits == 0 or len(s.split()) > 60 or BAD.search(s):
                continue
            lo, hi = REGION.get(name, (0.0, 1.0))
            score = hits + (1 if lo <= i / total <= hi else 0)
            if score > best_score:
                best, best_score = s, score
        result[name] = best
    return result