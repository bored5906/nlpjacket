import os
import json
import matplotlib.pyplot as plt
from rouge_score import rouge_scorer

def calculate_rouge(reference, generated):
    """Calculate ROUGE-1, ROUGE-2, and ROUGE-L F1 scores for a single summary."""
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
    scores = scorer.score(reference, generated)
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
    # Ensure output directories exist mapping to your project structure
    os.makedirs(f"{output_dir}/outputs", exist_ok=True)
    os.makedirs(f"{output_dir}/graphs", exist_ok=True)

    all_results = {}
    
    # 1. Loop through and calculate scores for each method
    for model_name, summary_text in generated_summaries.items():
        all_results[model_name] = calculate_rouge(reference_abstract, summary_text)

    # 2. Save results to JSON
    json_path = f"{output_dir}/outputs/rouge_results.json"
    with open(json_path, 'w') as f:
        json.dump(all_results, f, indent=4)

    # 3. Generate and save the comparison graph
    models = list(all_results.keys())
    rouge1 = [all_results[m]['ROUGE-1'] for m in models]
    rouge2 = [all_results[m]['ROUGE-2'] for m in models]
    rougeL = [all_results[m]['ROUGE-L'] for m in models]

    x = range(len(models))
    width = 0.25

    plt.figure(figsize=(10, 6))
    plt.bar([pos - width for pos in x], rouge1, width, label='ROUGE-1', color='#4C72B0')
    plt.bar(x, rouge2, width, label='ROUGE-2', color='#55A868')
    plt.bar([pos + width for pos in x], rougeL, width, label='ROUGE-L', color='#C44E52')

    plt.xticks(x, models)
    plt.ylabel('F1 Score')
    plt.title('ROUGE Score Comparison Across Models')
    plt.legend(loc='lower right')
    
    graph_path = f"{output_dir}/graphs/rouge_comparison.png"
    plt.savefig(graph_path)
    plt.close()

    return all_results