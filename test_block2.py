import pandas as pd
from src.preprocessing import clean_text, split_sentences
from src.model import summarize

df = pd.read_csv("dataset/dataset.csv")
sents = split_sentences(clean_text(df.loc[0, "article"]))
print("Sentences in paper:", len(sents))

result = summarize(sents, mode="compare", length="medium")
for name, text in result.items():
    print(f"\n=== {name.upper()} ({len(text.split())} words) ===")
    print(text[:600], "...")

print("\nAuthor's abstract:\n", df.loc[0, "abstract"][:600])