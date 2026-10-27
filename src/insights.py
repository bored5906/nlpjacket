import re
from collections import Counter

import spacy
import yake


# Load the English NLP model once and reuse it across requests.
nlp = spacy.load("en_core_web_sm")

KEEP_ENTITIES = {"PERSON", "ORG", "GPE", "LOC", "NORP", "PRODUCT", "EVENT"}

# Existing cleanup pattern used by keyword extraction and insight selection.
BAD = re.compile(r"@xmath|\$|\[|\]|_|\+|\d{5,}")

# False positives observed in the current technical-paper output.
ENTITY_NOISE = {
    "eq", "svm", "f1", "rbf", "rp", "lime", "linear", "recall",
    "non-zero", "bayesian", "acoustic", "magenta", "n", "n.",
    "w", "christianity", "wolf",
}

# Mathematical symbols and formula fragments.
FORMULA_NOISE = re.compile(r"[Ωω∑√≈≠≤≥×÷=<>%$@{}\[\]_^()]")

# Common paper artefacts incorrectly identified as entities.
PAPER_ARTEFACT = re.compile(
    r"^(?:table|tab\.?|figure|fig\.?|equation|eq\.?)\s*\d*\s*:?[.]?$",
    re.IGNORECASE,
)

CUES = {
    "objective": [
        "we propose", "we present", "in this paper", "this paper",
        "we investigate", "we study", "aim", "goal",
    ],
    "method": [
        "we use", "we used", "we apply", "we employ", "based on",
        "method", "approach", "algorithm",
    ],
    "findings": [
        "results show", "we found", "we find", "shows that",
        "indicates", "demonstrate", "significant",
    ],
    "limitations": [
        "limitation", "however", "future work", "cannot",
        "not able", "fail", "drawback",
    ],
}

REGION = {
    "objective": (0.0, 0.25),
    "findings": (0.65, 1.0),
    "limitations": (0.65, 1.0),
}


def extract_keywords(text, ngram="1-2", top=10):
    """YAKE finds keyphrases; a POS check keeps phrases containing a noun."""
    n = int(ngram.split("-")[1])

    raw = yake.KeywordExtractor(
        lan="en",
        n=n,
        top=top * 3,
        dedupLim=0.7,
    ).extract_keywords(text)

    kept, seen = [], set()

    for term, score in raw:
        term = term.lower().strip()

        if BAD.search(term) or term in seen:
            continue

        if not any(
            token.pos_ in ("NOUN", "PROPN")
            for token in nlp(term)
        ):
            continue

        seen.add(term)
        kept.append((term, score))

    kept = kept[:top]

    if not kept:
        return []

    best = min(score for _, score in kept) or 1e-6

    return [
        {"term": term, "score": round(best / score, 2)}
        for term, score in kept
    ]


def _is_valid_entity(raw_entity, label):
    """Reject obvious PDF, formula, and technical-term false positives."""
    name = " ".join(raw_entity.split()).strip(
        " \t\n.,;:()[]{}\"'"
    )
    normalized = name.casefold()

    if not name or BAD.search(name):
        return False

    if PAPER_ARTEFACT.fullmatch(name):
        return False

    if normalized in ENTITY_NOISE:
        return False

    # Reject equation symbols and fragments such as f(x) or Ω(g).
    if FORMULA_NOISE.search(name):
        return False

    # Reject numeric values and extracted citation/year artefacts.
    if not re.search(r"[A-Za-z]", name):
        return False

    if re.search(r"\d{2,}", name):
        return False

    # Reject malformed spans mixing a person's name with an institution.
    if label == "PERSON" and re.search(
        r"\b(university|institute|college|laboratory|department)\b",
        name,
        re.IGNORECASE,
    ):
        return False

    words = name.split()

    # Very short fragments are usually extraction noise.
    if len(name) <= 2:
        return (
            normalized in {"us", "uk", "eu", "un"}
            and label in {"GPE", "ORG"}
        )

    # Single lowercase words are usually ordinary vocabulary.
    # Multiword names such as "San Francisco" remain eligible.
    if len(words) == 1 and not name[0].isupper():
        return False

    # Short uppercase tokens often originate from equations or tables.
    if len(words) == 1 and name.isupper() and len(name) <= 3:
        if normalized not in {
            "usa", "uk", "eu", "un", "ibm", "acm", "ieee", "kdd"
        }:
            return False

    return True


def extract_entities(text, per_type=8, max_chars=100000):
    """Extract cleaned spaCy entities, grouped by type and frequency.

    Returns a dictionary compatible with the existing frontend:
        {"PERSON": ["Name One"], "ORG": ["Example Organisation"]}
    """
    doc = nlp(text[:max_chars])

    counts = {}
    display_names = {}

    for entity in doc.ents:
        if entity.label_ not in KEEP_ENTITIES:
            continue

        name = " ".join(entity.text.split()).strip(
            " \t\n.,;:()[]{}\"'"
        )

        if not _is_valid_entity(name, entity.label_):
            continue

        # Deduplicate case-insensitively while preserving the display form.
        normalized = name.casefold()
        label = entity.label_

        counts.setdefault(label, Counter())[normalized] += 1

        display_names.setdefault(label, {}).setdefault(
            normalized, name
        )

    return {
        label: [
            display_names[label][entity]
            for entity, _ in counter.most_common(per_type)
        ]
        for label, counter in counts.items()
    }


def key_insights(sentences):
    """Pick cue-bearing sentences while favouring relevant paper sections."""
    total = len(sentences)
    result = {}

    for name, cues in CUES.items():
        best, best_score = "", 0

        for index, sentence in enumerate(sentences):
            low = sentence.lower()
            hits = sum(cue in low for cue in cues)

            if (
                hits == 0
                or len(sentence.split()) > 60
                or BAD.search(sentence)
            ):
                continue

            lo, hi = REGION.get(name, (0.0, 1.0))
            position = index / total if total else 0.0
            score = hits + (1 if lo <= position <= hi else 0)

            if score > best_score:
                best, best_score = sentence, score

        result[name] = best

    return result