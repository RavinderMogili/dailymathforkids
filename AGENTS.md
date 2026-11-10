# Local verification

- Run `npm run test:unit -- --runInBand` for the mocked frontend unit suite. The daily challenge tests also invoke Python, which needs `markdown2` available for HTML rendering tests.
- Run `python -m unittest discover -s scripts -p test_daily_challenges.py` for challenge generation, answer alignment, SVG structure, and combinatorics checks without network access.
- Daily quiz generation is in `scripts/gen_site.py`; original challenge templates and controlled SVG diagrams are in `scripts/daily_challenges.py`.
- Do not run the full daily generator just to test templates: it can call LLM services and upsert quizzes when credentials are configured. Import the pure generation/rendering functions instead.
- Daily scoring in the sibling API is positional: questions 1–4 are easy, 5–8 medium, and 9+ hard. Daily pages append two hard illustrated challenge questions (Q11–Q12) after the original ten; do not use these challenges to replace curated pool questions.
