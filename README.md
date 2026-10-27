# PaperLens: Research Paper Summarization and Key Insight Extraction System

BCA 5th Semester NLP Project.

PaperLens takes a research paper (a PDF upload or an arXiv ID) and returns a summary, keywords, named entities, key insights, section summaries, a pipeline trace and ROUGE evaluation scores. Everything runs locally. No paid services or API keys are needed.

## Overview

The system compares three summarization approaches:

| Approach | Description |
|---|---|
| Lead baseline | The first sentences of the paper, up to a word budget. Used as a reference point. |
| TF-IDF | Each sentence is scored by the average TF-IDF weight of its words. |
| TextRank | Sentences are linked by cosine similarity of their TF-IDF vectors, then ranked with PageRank. |

All three are extractive: they select existing sentences and do not generate new text. A redundancy filter stops near-duplicate sentences from being selected.

Evaluation uses ROUGE-1, ROUGE-2 and ROUGE-L (precision, recall and F1) against the author's own abstract, plus compression ratio.

## NLP techniques used

Tokenization, lowercasing, stop-word removal, lemmatization (stemming for comparison), part-of-speech tagging, named entity recognition, n-grams, TF-IDF, cosine similarity, extractive text summarization.

Not used: word embeddings, transformer models, sentiment analysis, classification. Transformer-based abstractive summarization is listed as future scope.

## Processing pipeline

1. PDF text extraction (PyMuPDF)
2. Section detection (rule-based heading search)
3. Cleaning (citations, page numbers, references, broken hyphens, placeholders)
4. Sentence splitting and filtering of formula-heavy sentences
5. Preprocessing (lowercase, tokenize, remove stop-words, lemmatize or stem)
6. TF-IDF feature extraction
7. Summarization (lead baseline, TF-IDF, TextRank)
8. Keyword extraction (YAKE with a noun filter)
9. Named entity recognition (spaCy)
10. Key insight extraction (cue phrases and position in the paper)
11. Section summaries
12. ROUGE evaluation against the paper's abstract
13. Storage in SQLite and audit logging

The Pipeline Trace tab in the app shows the time and a short output preview for each stage.

## Requirements

- Python 3.11 recommended (3.10 also works)
- An internet connection for the first setup (library downloads, NLTK data, spaCy model), for fetching arXiv papers, and for web fonts
- About 1 GB of free disk space
- Windows, macOS or Linux

Python libraries (listed in `requirements.txt`): flask, pymupdf, nltk, spacy, scikit-learn, pandas, numpy, matplotlib, wordcloud, networkx, yake, rouge-score, datasets, requests.

Language model and data downloaded separately: the spaCy model `en_core_web_sm` and the NLTK packages `punkt`, `punkt_tab`, `stopwords` and `wordnet`.

## Installation

Run all commands from the project root folder.

**1. Create and activate a virtual environment**

Windows (PowerShell):
```
python -m venv venv
venv\Scripts\activate
```
If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip activation and call `.\venv\Scripts\python.exe` directly in every command below.

macOS / Linux:
```
python3 -m venv venv
source venv/bin/activate
```

**2. Install the libraries**
```
pip install -r requirements.txt
```

**3. Download the spaCy model**
```
python -m spacy download en_core_web_sm
```

**4. Download the NLTK data**
```
python -c "import nltk; [nltk.download(p) for p in ['punkt','punkt_tab','stopwords','wordnet']]"
```

## Running the web app

```
python app/app.py
```
Open http://127.0.0.1:5000 in a browser. The first request is slower because the models load. Press Ctrl+F5 after changing any frontend file.

**Using the app**
1. Drop a text-based PDF into the upload box, or type an arXiv ID such as `1706.03762` in the box beneath it.
2. Choose a mode: Fast (TF-IDF only), Accurate (TextRank only) or Compare (lead baseline, TF-IDF and TextRank).
3. Choose a length: Short (about 100 words), Medium (about 200) or Long (about 300).
4. Optionally open Advanced options to switch between lemmatization and stemming, and between 1-2 and 1-3 word keyword phrases.
5. Click Process paper. Results appear in seven tabs: Summary, Key insights, Keywords, Entities, Sections, Pipeline trace and Evaluation.

Each open paper is a tab at the top of the page. The History page records every action.

**Frontend mock mode:** `app/static/app.js` has a setting `USE_MOCK` near the top. When `true`, the page shows sample data from `app/static/mock.json` without the backend. It must be `false` for real processing.

## Running the dataset evaluation

The evaluation scores all three methods on papers from the dataset and writes results to `results/`.

1. Create the dataset sample once. In Python or a notebook:
```python
from datasets import load_dataset
import pandas as pd
ds = load_dataset("ccdv/arxiv-summarization", split="test[:100]")
pd.DataFrame(ds[:100]).to_csv("dataset/dataset.csv", index=False)
```
2. Run:
```
python -m src.evaluation
```
Outputs:
- `results/outputs/rouge_results.json` (average ROUGE F1 per method)
- `results/graphs/rouge_comparison.png` (bar chart)

By default it scores the first 50 papers at Medium length with lemmatization. Edit the arguments of `evaluate_dataset` in `src/evaluation.py` to try other settings, for example `method="stem"`.

## Dataset

- Source: Hugging Face dataset `ccdv/arxiv-summarization` (scientific papers from arXiv)
- Fields used: `article` (full body text, input) and `abstract` (author-written summary, ROUGE reference)
- Sample used: the first 100 records of the test split, with the first 50 scored in the default evaluation
- Format: CSV exported to `dataset/dataset.csv`
- Note: the text is pre-processed. It is lowercased, math is replaced by placeholders such as `@xmath0`, and citations are replaced by `@xcite`. Real PDFs are noisier, so results on uploaded papers differ.

## Project structure

```
NLP_Project/
  dataset/
    dataset.csv              Sample of the arXiv summarization dataset
  notebooks/
    analysis.ipynb           Dataset exploration
  src/
    preprocessing.py         PDF reading, cleaning, tokenization, stop-words, lemmatization, arXiv fetch
    model.py                 Lead baseline, TF-IDF summarizer, TextRank summarizer
    insights.py              Keywords, named entities, key insights
    sections.py              Section detection and section summaries
    evaluation.py            ROUGE scoring, dataset evaluation, chart
    pipeline.py              Runs every stage and records timings
    prediction.py            Single entry point used by the web app
  app/
    app.py                   Flask server and API routes
    database.py              SQLite storage (papers, history, settings)
    templates/index.html     Page structure
    static/style.css         Styles and theme variables
    static/app.js            Frontend logic
    static/mock.json         Sample response and API contract
  results/
    graphs/                  Charts
    outputs/                 JSON results
  uploads/                   Uploaded and downloaded PDFs (created automatically)
  nlp.db                     SQLite database (created automatically)
  README.md
  requirements.txt
  Project_Report.pdf
```

## API endpoints

| Method | Route | Purpose |
|---|---|---|
| POST | `/api/process` | Form data: `file` (PDF) or `arxiv` (ID or link), and `options` (JSON with mode, length, normalization, ngram). Returns the result JSON. |
| GET | `/api/papers` | List saved papers |
| GET, DELETE | `/api/papers/<id>` | Load or delete one saved result |
| GET, DELETE | `/api/history` | Read or clear the audit log |
| GET, POST | `/api/settings` | Read or save default mode, length and theme |

Errors are returned as `{"error": "message"}` with a non-200 status.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `OSError: Can't find model 'en_core_web_sm'` | Run the spaCy download command (step 3) using the venv's Python. |
| `LookupError: Resource stopwords not found` | Run the NLTK download command (step 4). |
| `ModuleNotFoundError` | The library is missing. Run `pip install -r requirements.txt` with the venv active. |
| Page shows sample data (not your paper) | `USE_MOCK` is still `true` in `app/static/app.js`, or the browser cached the old file. Fix and press Ctrl+F5. |
| "Almost no text found" | The PDF is scanned (images of pages). Use a text-based PDF. If you cannot select text with the mouse, it is scanned. |
| "Too little readable text" | The PDF has few full sentences (slides, tables, heavy math). |
| Sections or Evaluation tab is empty | No clear "Abstract" heading line was found, so there is no reference to score against. This is a known limit. |
| arXiv download fails | Check the internet connection and the ID format (for example `2301.12345`). |
| Fonts look different | Fonts load from Google Fonts. Without internet the fallback fonts are used. |

## Limitations

- Summaries are extractive, so they can read choppily and may include sentences that need surrounding context.
- ROUGE measures word overlap with the abstract, not meaning or readability.
- Section detection relies on headings that sit on their own line. It misses some layouts.
- Key insights use cue phrases, so a category can come back empty.
- The spaCy model `en_core_web_sm` is trained on general text, so it can miss scientific terms. It works poorly on all-lowercase text such as the dataset.
- Formulas, tables and figure captions are only partly filtered out.
- Scanned PDFs are not supported (no OCR).
- Only modern arXiv IDs (for example `2301.12345`) are supported, not old-style IDs like `hep-th/9901001`.

## Ethics and privacy

- The dataset and the papers fetched from arXiv are openly available. Fetch only open-access papers and avoid sending many requests in quick succession.
- Uploaded PDFs are stored in `uploads/` and results in `nlp.db` on the local machine only. Nothing is sent to any external service apart from arXiv downloads and web fonts.
- Do not upload confidential or personal documents without authorization.
- Automatic summaries can omit or distort important points. They support reading and should not replace it.

## Future scope

- Abstractive summarization with a pretrained transformer such as BART
- Sentence embeddings for similarity in place of TF-IDF
- A scientific NER model such as scispaCy
- OCR support for scanned PDFs
- Support for additional open-access sources (PubMed Central, bioRxiv)
- Linking each summary sentence to its page in the PDF

## Credits

Libraries: Flask, PyMuPDF, NLTK, spaCy, scikit-learn, NetworkX, YAKE, rouge-score, Pandas, NumPy, Matplotlib, Hugging Face datasets, Requests. Dataset: ccdv/arxiv-summarization.

Author: (name, roll number, course, institution, year)