from src.pipeline import run_pipeline


def run(pdf_path, options=None):
    """The one function the web app calls. options: mode, length, normalization, ngram."""
    options = options or {}
    return run_pipeline(
        pdf_path,
        mode=options.get("mode", "accurate"),
        length=options.get("length", "medium"),
        normalization=options.get("normalization", "lemma"),
        ngram=options.get("ngram", "1-2"),
    )