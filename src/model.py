import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.preprocessing import preprocess_sentence

WORD_TARGET = {"short": 100, "medium": 200, "long": 300}
REDUNDANCY_LIMIT = 0.6


def build_tfidf(sentences, method="lemma"):
    """Turn each sentence into a row of TF-IDF numbers."""
    docs = [" ".join(preprocess_sentence(s, method)) for s in sentences]
    return TfidfVectorizer(norm=None).fit_transform(docs)


def pick_top(scores, sentences, matrix, length):
    """Take best-scoring sentences until the word budget is full, skipping repeats."""
    budget = WORD_TARGET[length]
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    chosen, words = [], 0
    for i in order:
        if words >= budget:
            break
        if chosen and cosine_similarity(matrix[i], matrix[chosen]).max() > REDUNDANCY_LIMIT:
            continue                              # too similar to a sentence we already have
        chosen.append(i)
        words += len(sentences[i].split())
    return " ".join(sentences[i] for i in sorted(chosen))   # back to paper order


def lead_summary(sentences, length="medium"):
    """Baseline: the first sentences, until the word budget is full."""
    out, words = [], 0
    for s in sentences:
        if words >= WORD_TARGET[length]:
            break
        out.append(s)
        words += len(s.split())
    return " ".join(out)


def tfidf_summary(sentences, length="medium", method="lemma"):
    """Approach 1: a sentence scores high if its words are important on average."""
    matrix = build_tfidf(sentences, method)
    sums = matrix.sum(axis=1).A1               # total importance per sentence
    counts = matrix.getnnz(axis=1)             # number of distinct words per sentence
    scores = [s / c if c >= 4 else 0 for s, c in zip(sums, counts)]   # average, ignore tiny ones
    return pick_top(scores, sentences, matrix, length)


def textrank_summary(sentences, length="medium", method="lemma"):
    """Approach 2: a sentence scores high if many similar sentences point to it."""
    matrix = build_tfidf(sentences, method)
    similarity = cosine_similarity(matrix)     # grid: how alike is every pair of sentences
    graph = nx.from_numpy_array(similarity)    # sentences = dots, similarity = line strength
    ranks = nx.pagerank(graph, weight="weight", max_iter=200)
    scores = [ranks[i] for i in range(len(sentences))]
    return pick_top(scores, sentences, matrix, length)


def summarize(sentences, mode="accurate", length="medium", method="lemma"):
    """Run the methods the chosen mode needs. Output matches mock.json 'summaries'."""
    if mode == "fast":
        return {"tfidf": tfidf_summary(sentences, length, method)}
    if mode == "accurate":
        return {"textrank": textrank_summary(sentences, length, method)}
    return {"lead": lead_summary(sentences, length),
            "tfidf": tfidf_summary(sentences, length, method),
            "textrank": textrank_summary(sentences, length, method)}