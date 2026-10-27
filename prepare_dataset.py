import pandas as pd
import importlib

try:
	load_dataset = importlib.import_module("datasets").load_dataset
except ModuleNotFoundError as exc:
	if exc.name != "datasets":
		raise
	raise SystemExit(
		"The 'datasets' package is required. Install it with: "
		"python -m pip install datasets"
	) from exc

# 1. Load the first 100 samples from the test split of the arXiv summarization dataset
print("Downloading dataset (100 samples)...")
dataset = load_dataset("ccdv/arxiv-summarization", split="test[:100]")

# 2. Inspect keys and record count
print(f"Dataset keys: {dataset.column_names}")
print(f"Total samples loaded: {len(dataset)}")

# 3. Convert Hugging Face dataset to a pandas DataFrame
df = pd.DataFrame(dataset)

# 4. Calculate word counts for articles and abstracts
df["article_word_count"] = df["article"].apply(lambda text: len(text.split()))
df["abstract_word_count"] = df["abstract"].apply(lambda text: len(text.split()))

# 5. Display average statistics
avg_article_words = df["article_word_count"].mean()
avg_abstract_words = df["abstract_word_count"].mean()

print(f"Average words per article: {avg_article_words:.1f}")
print(f"Average words per abstract: {avg_abstract_words:.1f}")

# 6. Save clean data to dataset/dataset.csv
df.to_csv("dataset/dataset.csv", index=False)
print("Saved successfully to dataset/dataset.csv")