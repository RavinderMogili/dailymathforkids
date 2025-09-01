# scripts/gen_site.py
import os, pathlib, datetime, sys
import markdown2

# Optional OpenAI import guarded so script still runs if SDK missing or key absent
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
DAILY_DIR.mkdir(parents=True, exist_ok=True)

TITLE = os.getenv("SITE_TITLE", "Daily Math for Kids")

def safe_generate_today():
    """Try to create today's page via OpenAI. If anything fails, continue gracefully."""
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not OpenAI or not api_key:
        print("INFO: Skipping OpenAI generation (SDK or API key missing).")
        return

    os.environ["OPENAI_API_KEY"] = api_key
    client = OpenAI()
    today = datetime.date.today().isoformat()
    slug = today
    md_path = DAILY_DIR / f"{slug}.md"
    html_path = DAILY_DIR / f"{slug}.html"

    prompt = f"""
Create 5 kid-friendly math problems for Grades 2–4 in Canadian primary school.

Guidelines:
- Mix problem types: 2 addition, 1 subtraction, 1 multiplication, 1 word problem.
- Use numbers under 100.
- Keep wording short and clear.
- Make the word problem about everyday life (fruits, toys, sharing, money).
- Encourage kids gently.
- After the problems, add an 'Answers' section with clear step-by-step answers.

Format in Markdown:
# Daily Math - {today}
## Problems
1. ...
2. ...
## Answers
1. ...
2. ...
"""

    try:
        resp = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = resp.output_text.strip()
        if not text:
            print("WARN: OpenAI returned empty text; skipping page write.")
            return
        md_path.write_text(text + "\n", encoding="utf-8")
        body_html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])
        page_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{TITLE} - {today}</title><link rel="stylesheet" href="../styles.css"/></head>
<body>
<header><a href="../index.html">{TITLE}</a></header>
<main class="container">
{body_html}
<p class="back"><a href="../index.html"><- Back to Home</a></p>
</main>
<footer>© {datetime.date.today().year} • Auto-generated daily</footer>
</body></html>"""
        html_path.write_text(page_html, encoding="utf-8")
        print(f"INFO: Wrote {html_path}")
    except Exception as e:
        # Keep the job green for sitemap/index rebuild
        print(f"ERROR: OpenAI generation failed: {e}", file=sys.stderr)

def rebuild_index_and_sitemap():
    pages = sorted(DAILY_DIR.glob("*.html"), key=lambda p: p.name, reverse=True)
    # Build index.html (latest + recent)
    if pages:
        latest = pages[0].stem
        today_link = f"daily/{latest}.html"
    else:
        latest = None
        today_link = None

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{TITLE}</title>
  <meta name="description" content="Five new, kid-friendly math problems every day, plus answers."/>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>
  <header>{TITLE}</header>
  <main class="container">
    <section class="hero">
      <h1>Practice a little every day</h1>
      <p>Five kid-friendly math problems posted daily. Simple, positive, and free.</p>
      <p><strong>Latest:</strong> {"<a href='"+today_link+"'>Open today</a>" if today_link else "First post arrives after the first daily run."}</p>
    </section>
    <section>
      <h2>Recent days</h2>
      <ul class="list">
        {''.join(f'<li><a href="daily/{p.name}">Daily Math - {p.stem}</a></li>' for p in pages[:30]) if pages else "<li>No daily pages yet.</li>"}
      </ul>
    </section>
  </main>
  <footer>© {datetime.date.today().year} • Auto-generated daily</footer>
</body></html>"""
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")

    # Build sitemap.xml that works for project Pages (user.github.io/repo/)
    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_USERNAME/dailymathforkids")
    user, repo_name = (repo.split("/", 1) + [""])[:2]
    base_url = f"https://{user}.github.io/{repo_name}/"
    urls = [base_url] + [base_url + f"daily/{p.name}" for p in sorted(DAILY_DIR.glob("*.html"))]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc></url>" for u in urls]
    sitemap.append("</urlset>\n")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    print("INFO: Rebuilt index.html and sitemap.xml")

if __name__ == "__main__":
    safe_generate_today()
    rebuild_index_and_sitemap()
