import os
import json
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from rouge_score import rouge_scorer

SCORER = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)


def clean_reference(text):
    """Remove math placeholders and citation tags from reference text before scoring."""
    text = re.sub(r"@xmath\d*|@xcite|\$|\[|\]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def calculate_rouge(reference, generated):
    """Calculate ROUGE-1, ROUGE-2, and ROUGE-L F1 scores for a single summary."""
    cleaned_ref = clean_reference(reference)
    scores = SCORER.score(cleaned_ref, generated)
    return {
        'ROUGE-1': round(scores['rouge1'].fmeasure, 4),
        'ROUGE-2': round(scores['rouge2'].fmeasure, 4),
        'ROUGE-L': round(scores['rougeL'].fmeasure, 4)
    }


def evaluate_multiple_models(reference_abstract, generated_summaries, output_dir="results"):
    """
    Loops through multiple summarization methods, compares them to the abstract, 
    and generates the evaluation JSON and bar chart.
    """
    os.makedirs(f"{output_dir}/outputs", exist_ok=True)
    os.makedirs(f"{output_dir}/graphs", exist_ok=True)

    all_results = {}
    for model_name, summary_text in generated_summaries.items():
        all_results[model_name] = calculate_rouge(reference_abstract, summary_text)

    # Save single-run results to JSON
    json_path = f"{output_dir}/outputs/rouge_results.json"
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=4)

    # Generate and save the comparison graph
    models = list(all_results.keys())
    rouge1 = [all_results[m]['ROUGE-1'] for m in models]
    rouge2 = [all_results[m]['ROUGE-2'] for m in models]
    rougeL = [all_results[m]['ROUGE-L'] for m in models]

    x = list(range(len(models)))
    width = 0.25

    plt.figure(figsize=(8, 5))
    plt.bar([pos - width for pos in x], rouge1, width, label='ROUGE-1', color='#4C72B0')
    plt.bar(x, rouge2, width, label='ROUGE-2', color='#55A868')
    plt.bar([pos + width for pos in x], rougeL, width, label='ROUGE-L', color='#C44E52')

    plt.xticks(x, [m.upper() for m in models])
    plt.ylabel('F1 Score')
    plt.title('ROUGE Score Comparison Across Models')
    plt.legend(loc='lower right')
    plt.tight_layout()
    
    graph_path = f"{output_dir}/graphs/rouge_comparison.png"
    plt.savefig(graph_path, dpi=150)
    plt.close()

    return all_results


def evaluate_dataset(csv_path="dataset/dataset.csv", n=50, length="medium", method="lemma", output_dir="results"):
    """
    Batch evaluation: runs all three methods on n dataset papers, averages scores,
    and produces results/outputs/rouge_results.json and results/graphs/rouge_comparison.png.
    """
    import pandas as pd
    from src.model import summarize
    from src.preprocessing import clean_text, split_sentences

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Run prepare_dataset.py first.")

    df = pd.read_csv(csv_path).head(n)
    totals = {}
    used = 0

    print(f"Evaluating dataset ({len(df)} papers) using length={length}, method={method}...")
    for i, row in df.iterrows():
        sents = split_sentences(clean_text(str(row["article"])))
        if len(sents) < 8:
            continue
        
        sums = summarize(sents, mode="compare", length=length, method=method)
        ref = str(row["abstract"])

        for model_name, summary_text in sums.items():
            scores = calculate_rouge(ref, summary_text)
            bucket = totals.setdefault(model_name, {"ROUGE-1": 0.0, "ROUGE-2": 0.0, "ROUGE-L": 0.0})
            for k in bucket:
                bucket[k] += scores[k]
        used += 1
        if (i + 1) % 10 == 0 or (i + 1) == len(df):
            print(f"Processed paper {i + 1}/{len(df)}")

    if used == 0:
        print("No valid papers found for evaluation.")
        return {}

    averages = {
        m: {k: round(v / used, 4) for k, v in metrics.items()}
        for m, metrics in totals.items()
    }

    os.makedirs(f"{output_dir}/outputs", exist_ok=True)
    os.makedirs(f"{output_dir}/graphs", exist_ok=True)

    json_path = f"{output_dir}/outputs/rouge_results.json"
    with open(json_path, 'w') as f:
        json.dump({
            "papers_used": used,
            "length": length,
            "method": method,
            "averages": averages
        }, f, indent=4)

    # Plot averages
    models = list(averages.keys())
    rouge1 = [averages[m]['ROUGE-1'] for m in models]
    rouge2 = [averages[m]['ROUGE-2'] for m in models]
    rougeL = [averages[m]['ROUGE-L'] for m in models]

    x = list(range(len(models)))
    width = 0.25

    plt.figure(figsize=(8, 5))
    plt.bar([pos - width for pos in x], rouge1, width, label='ROUGE-1', color='#4C72B0')
    plt.bar(x, rouge2, width, label='ROUGE-2', color='#55A868')
    plt.bar([pos + width for pos in x], rougeL, width, label='ROUGE-L', color='#C44E52')

    plt.xticks(x, [m.upper() for m in models])
    plt.ylabel('Average F1 Score')
    plt.title(f'Dataset Evaluation: Average ROUGE Scores ({used} Papers)')
    plt.legend(loc='lower right')
    plt.tight_layout()

    graph_path = f"{output_dir}/graphs/rouge_comparison.png"
    plt.savefig(graph_path, dpi=150)
    plt.close()

    print(f"Evaluation complete! Results saved to {json_path} and {graph_path}")
    return averages


if __name__ == "__main__":
    evaluate_dataset(n=5)
