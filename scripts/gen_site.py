import os, pathlib, datetime
from openai import OpenAI
import markdown2

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
DAILY_DIR.mkdir(parents=True, exist_ok=True)

TITLE = os.getenv("SITE_TITLE", "Daily Math for Kids")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

today = datetime.date.today().isoformat()  # YYYY-MM-DD
slug = today
md_path = DAILY_DIR / f"{slug}.md"
html_path = DAILY_DIR / f"{slug}.html"

prompt = """
Create 5 kid-friendly primary school math problems for Canada (Grades 1-5).
Mix types: addition, subtraction, multiplication, division, and one simple word problem.
Use small numbers and clear wording. Encourage the child gently.
After the problems, add an 'Answers' section with answers 1-5 on separate lines.
Return in clean Markdown with:
- H1: "Daily Math - YYYY-MM-DD"
- H2: "Problems"
- Numbered list (1-5)
- H2: "Answers"
- Numbered list (1-5)
Keep language simple and positive.
""".replace("YYYY-MM-DD", today)

resp = client.responses.create(
    model="gpt-4o-mini",
    input=prompt,
)
text = resp.output_text.strip()

# Save Markdown
md_path.write_text(text + "\n", encoding="utf-8")

# Convert to HTML page
body_html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])
page_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title} - {today}</title>
  <link rel="stylesheet" href="../styles.css" />
</head>
<body>
  <header><a href="../index.html">{title}</a></header>
  <main class="container">
    {body}
    <p class="back"><a href="../index.html"><- Back to Home</a></p>
  </main>
  <footer>© {year} • Auto-generated daily</footer>
</body>
</html>""".format(title=TITLE, today=today, body=body_html, year=datetime.date.today().year)
html_path.write_text(page_html, encoding="utf-8")

# Build/refresh index.html with latest 30 days
pages = sorted(DAILY_DIR.glob("*.html"), key=lambda p: p.name, reverse=True)
links = []
for p in pages[:30]:
    date_str = p.stem
    try:
        d = datetime.date.fromisoformat(date_str)
        pretty = d.strftime("%b %d, %Y")
    except Exception:
        pretty = date_str
    links.append('<li><a href="daily/{name}">Daily Math - {pretty}</a></li>'.format(name=p.name, pretty=pretty))

index_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <meta name="description" content="Five new, kid-friendly math problems every day, plus answers." />
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header>{title}</header>
  <main class="container">
    <section class="hero">
      <h1>Practice a little every day</h1>
      <p>Five kid-friendly math problems posted daily. Simple, positive, and free.</p>
      <p><strong>Today:</strong> <a href="daily/{slug}.html">Start here -></a></p>
    </section>
    <section>
      <h2>Recent days</h2>
      <ul class="list">
        {links}
      </ul>
    </section>
  </main>
  <footer>© {year} • Auto-generated daily</footer>
</body>
</html>""".format(title=TITLE, slug=slug, links=("".join(links) if links else "<li>First post arrives after the first daily run.</li>"), year=datetime.date.today().year)
(ROOT / "index.html").write_text(index_html, encoding="utf-8")

# Simple sitemap for SEO
base = os.getenv('GITHUB_REPOSITORY', 'YOUR_USERNAME/dailymathforkids').split('/')[0]
base_url = "https://{user}.github.io/dailymathforkids/".format(user=base)
urls = [base_url] + [base_url + "daily/{name}".format(name=p.name) for p in sorted(DAILY_DIR.glob('*.html'))]
sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for u in urls:
    sitemap.append("  <url><loc>{}</loc></url>".format(u))
sitemap.append("</urlset>\n")
(ROOT / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")

print("Generated", html_path, "and updated index.html")
