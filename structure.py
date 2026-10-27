import os

folders = ["dataset", "notebooks", "src", "app/templates", "app/static",
           "results/graphs", "results/outputs", "uploads"]
files = ["README.md", "requirements.txt",
         "src/__init__.py", "src/preprocessing.py", "src/model.py",
         "src/insights.py", "src/evaluation.py", "src/pipeline.py", "src/prediction.py",
         "app/app.py", "app/database.py",
         "app/templates/index.html", "app/static/style.css",
         "app/static/app.js", "app/static/mock.json"]

for f in folders:
    os.makedirs(f, exist_ok=True)      # make folder if missing
for f in files:
    if not os.path.exists(f):
        open(f, "w").close()           # make empty file if missing
print("Structure ready")