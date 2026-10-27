import os
import re

import fitz                      # PyMuPDF, reads PDFs
import requests
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.tokenize import sent_tokenize, word_tokenize

STOP = set(stopwords.words("english"))
lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()


def extract_text(pdf_path):
    """Read every page of a PDF and join the text."""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def clean_text(text):
    """Remove noise so only the paper's real sentences remain."""
    text = re.sub(r"-\n(\w)", r"\1", text)                  # fix words split by hyphen at line end
    text = re.sub(r"@xmath\d*|@xcite", "", text)            # dataset placeholder tokens
    matches = list(re.finditer(r"\n\s*(references|bibliography)\s*\n", text, re.I))
    if matches:
        text = text[:matches[-1].start()]                   # cut everything after the last "References"
    text = re.sub(r"\[\d+(?:[,\s\-–]+\d+)*\]", "", text)    # remove citations like [12] or [3, 4]
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)             # remove lone page numbers
    text = re.sub(r"\s*\n\s*", " ", text)                   # join lines into flowing text
    text = re.sub(r"\s{2,}", " ", text)                     # collapse extra spaces
    return text.strip()


def split_sentences(text):
    """Split into sentences, dropping short fragments and symbol-heavy (formula) sentences."""
    kept = []
    for s in sent_tokenize(text):
        words = s.split()
        if len(words) < 5:
            continue
        real = sum(w.strip(".,;:()[]$_").isalpha() for w in words)   # words made of letters
        if real / len(words) >= 0.7:
            kept.append(s)
    return kept


def preprocess_sentence(sentence, method="lemma"):
    """Lowercase, tokenize, remove stop-words, then lemmatize or stem."""
    tokens = word_tokenize(sentence.lower())
    tokens = [t for t in tokens if t.isalpha() and t not in STOP]
    if method == "stem":
        return [stemmer.stem(t) for t in tokens]
    return [lemmatizer.lemmatize(t) for t in tokens]


def fetch_arxiv_pdf(id_or_url, save_dir="uploads"):
    """Download an arXiv paper as a PDF. Accepts '2301.12345' or a full arxiv.org link."""
    match = re.search(r"(\d{4}\.\d{4,5})", id_or_url)
    if not match:
        raise ValueError("Could not find an arXiv ID like 2301.12345")
    arxiv_id = match.group(1)
    response = requests.get(f"https://arxiv.org/pdf/{arxiv_id}", timeout=30,
                            headers={"User-Agent": "student-nlp-project"})
    response.raise_for_status()
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, f"{arxiv_id}.pdf")
    with open(path, "wb") as f:
        f.write(response.content)
    return path