import json
import os
import re

from rouge_score import rouge_scorer

SCORER = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)


def clean_reference(text):
    """Remove math placeholders from the author's abstract before scoring."""
    text = re.sub(r"@xmath\d*|@xcite|\$|\[|\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def evaluate_summary(summary, reference, source_words):
    """ROUGE F1 (plus rouge-1 precision/recall) against the reference, and compression ratio."""
    s = SCORER.score(clean_reference(reference), summary)
    return {
        "rouge1": round(s["rouge1"].fmeasure, 3),
        "rouge2": round(s["rouge2"].fmeasure, 3),
        "rougeL": round(s["rougeL"].fmeasure, 3),
        "rouge1_p": round(s["rouge1"].precision, 3),
        "rouge1_r": round(s["rouge1"].recall, 3),
        "compression": f"{len(summary.split()) / max(source_words, 1) * 100:.1f}%",
    }


def evaluate_dataset(csv_path="dataset/dataset.csv", n=50, length="medium", method="lemma"):
    """Run all three methods on n dataset papers, average the scores, save JSON and a chart."""
    import pandas as pd
    from src.model import summarize
    from src.preprocessing import clean_text, split_sentences

    df = pd.read_csv(csv_path).head(n)
    totals, used = {}, 0
    for i, row in df.iterrows():
        sents = split_sentences(clean_text(row["article"]))
        if len(sents) < 8:
            continue                                   # too short to summarize
        words = sum(len(s.split()) for s in sents)
        for name, summary in summarize(sents, "compare", length, method).items():
            scores = evaluate_summary(summary, row["abstract"], words)
            bucket = totals.setdefault(name, {"rouge1": 0, "rouge2": 0, "rougeL": 0})
            for key in bucket:
                bucket[key] += scores[key]
        used += 1
        print(f"paper {i + 1}/{len(df)} done")
    averages = {m: {k: round(v / used, 3) for k, v in s.items()} for m, s in totals.items()}

    os.makedirs("results/outputs", exist_ok=True)
    os.makedirs("results/graphs", exist_ok=True)
    with open("results/outputs/rouge_results.json", "w") as f:
        json.dump({"papers_used": used, "length": length, "method": method, "averages": averages}, f, indent=2)
    _plot(averages)
    return averages


def _plot(averages):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    metrics = ["rouge1", "rouge2", "rougeL"]
    width = 0.25
    for j, (method, scores) in enumerate(averages.items()):
        plt.bar([i + j * width for i in range(3)], [scores[m] for m in metrics], width, label=method)
    plt.xticks([i + width for i in range(3)], ["ROUGE-1", "ROUGE-2", "ROUGE-L"])
    plt.ylabel("F1 score")
    plt.title("Lead baseline vs TF-IDF vs TextRank")
    plt.legend()
    plt.savefig("results/graphs/rouge_comparison.png", dpi=150, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":          # run from project root:  python -m src.evaluation
    print(evaluate_dataset())