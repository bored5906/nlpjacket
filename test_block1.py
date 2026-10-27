import pandas as pd
import nltk

for pkg in ["punkt", "punkt_tab", "stopwords", "wordnet"]:
    nltk.download(pkg, quiet=True)

from src.preprocessing import clean_text, split_sentences, preprocess_sentence

df = pd.read_csv("dataset/dataset.csv")
print("Rows:", len(df), "| Columns:", list(df.columns))

raw = df.loc[0, "article"]
clean = clean_text(raw)
sents = split_sentences(clean)
print("Raw characters:  ", len(raw))
print("Clean characters:", len(clean))
print("Sentences:       ", len(sents))
print("First 2 sentences:", sents[:2])

# lemma vs stem: show words where the two methods disagree
examples = set()
for s in sents[:200]:
    lemma = preprocess_sentence(s, "lemma")
    stem = preprocess_sentence(s, "stem")
    for a, b in zip(lemma, stem):
        if a != b:
            examples.add((a, b))
print("\nlemma -> stem (first 12 differences):")
for a, b in sorted(examples)[:12]:
    print(f"  {a:15} -> {b}")