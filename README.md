# Weather Atlas

A static climate explorer that can be hosted directly on GitHub Pages.

## GitHub Pages

Push to `main`, then enable **Settings → Pages → GitHub Actions**. The workflow in
`.github/workflows/deploy-pages.yml` publishes the repository root automatically.

GitHub Pages cannot run the local Python API. The site therefore uses deterministic
demo observations when the API is unavailable; run `python app.py` locally to use
live Meteostat observations.

## Local development

```text
pip install pandas meteostat
python app.py
```

Open `http://localhost:8000`.
