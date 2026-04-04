import os, pathlib, datetime, sys, re
import markdown2

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
DAILY_DIR.mkdir(parents=True, exist_ok=True)

TITLE = os.getenv("SITE_TITLE", "Daily Math for Kids")
PUBLIC_API = os.getenv("PUBLIC_API_BASE", "https://YOUR_BACKEND_URL").rstrip("/")

# JS injected into every generated daily page
HELPERS_JS = r"""
<script>
(function enhanceProblems() {
  document.querySelectorAll('#problems-list > li').forEach(li => {
    const text = li.innerText;
    const en    = (text.match(/EN:\s*([\s\S]*?)\n\s*-\s*FR:/i)       || [])[1]?.trim() || '';
    const fr    = (text.match(/FR:\s*([\s\S]*?)\n\s*-\s*Grade Tag:/i) || [])[1]?.trim() || '';
    const hint  = (text.match(/Hint:\s*([\s\S]*?)\n\s*-\s*Steps:/i)  || [])[1]?.trim() || '';
    const steps = (text.match(/Steps:\s*([\s\S]*?)\n\s*-\s*Answer:/i) || [])[1]?.trim() || '';
    const ans   = (text.match(/Answer:\s*([\S]+)/i) || [])[1]?.trim() || '';
    const tag   = (text.match(/Grade Tag:\s*(G(?:1[0-2]|[1-9]))/i) || [])[1] || 'G3';

    li.dataset.level    = tag;
    li.dataset.answer   = ans;
    li.dataset.hint     = hint;
    li.dataset.question = en;

    function speak(t, lang) {
      const u = new SpeechSynthesisUtterance(t);
      u.lang = lang; u.rate = 0.95; u.pitch = 1.05;
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    }

    const stepsHtml = steps
      ? '<ul><li>' + steps.replace(/\n\s*-\s*/g, '</li><li>') + '</li></ul>'
      : '<ul><li>Break the problem into smaller parts.</li></ul>';

    const bar = document.createElement('div');
    bar.style.cssText = 'margin:8px 0;display:flex;flex-wrap:wrap;gap:6px;align-items:center';
    bar.innerHTML = `
      <span class="grade-badge">${tag.replace('G','Grade ')}</span>
      <button type="button" class="tts-en">🎧 EN</button>
      <button type="button" class="tts-fr">🎧 FR</button>
      <details class="hint-wrap" style="width:100%">
        <summary style="cursor:pointer;font-weight:600">Show hint</summary>
        <p style="margin:6px 0 0">${hint || 'Try drawing a picture or using counters!'}</p>
      </details>
      <details class="steps-wrap" style="width:100%">
        <summary style="cursor:pointer;font-weight:600">Show steps</summary>
        ${stepsHtml}
      </details>
      <details style="width:100%">
        <summary style="cursor:pointer;font-weight:600">Show answer</summary>
        <p style="margin:6px 0 0;font-weight:700">${ans || 'Check your steps!'}</p>
      </details>`;
    li.appendChild(bar);

    bar.querySelector('.tts-en').onclick = () => speak(en, 'en-CA');
    bar.querySelector('.tts-fr').onclick = () => speak(fr, 'fr-CA');
  });
})();

(function difficultyFilter() {
  const grades = ['G1','G2','G3','G4','G5','G6','G7','G8','G9','G10','G11','G12'];
  const labels = {G1:'Gr.1',G2:'Gr.2',G3:'Gr.3',G4:'Gr.4',G5:'Gr.5',G6:'Gr.6',
                  G7:'Gr.7',G8:'Gr.8',G9:'Gr.9',G10:'Gr.10',G11:'Gr.11',G12:'Gr.12'};
  const box = document.createElement('div');
  box.className = 'hero'; box.style.marginTop = '12px';
  box.setAttribute('aria-label','Choose difficulty');
  const stored = (() => { try { return JSON.parse(localStorage.getItem('dmk_lvl')) || 'G3'; } catch { return 'G3'; } })();
  box.innerHTML = '<strong>Your grade:</strong> ' +
    grades.map(g => `<label style="margin:0 4px"><input type="radio" name="lvl" value="${g}"${g===stored?' checked':''}> ${labels[g]}</label>`).join('');
  const h1 = document.querySelector('h1');
  if (h1) h1.after(box);

  function apply() {
    const lvl = (box.querySelector('input[name="lvl"]:checked') || {}).value || 'G3';
    try { localStorage.setItem('dmk_lvl', JSON.stringify(lvl)); } catch {}
    document.querySelectorAll('#problems-list > li').forEach(li => {
      li.style.opacity = (li.dataset.level === lvl) ? '1' : '0.35';
      li.style.pointerEvents = (li.dataset.level === lvl) ? '' : 'none';
    });
  }
  box.querySelectorAll('input[name="lvl"]').forEach(r => r.addEventListener('change', apply));
  apply();
})();
</script>
"""

def upsert_quiz_to_supabase(quiz_id, questions, answers):
    supabase_url = os.environ.get("SUPABASE_URL", "").strip()
    service_role  = os.environ.get("SUPABASE_SERVICE_ROLE", "").strip()
    if not supabase_url or not service_role:
        print("INFO: Supabase env vars not set — skipping quiz DB insert.")
        return
    try:
        import httpx
        r = httpx.post(
            f"{supabase_url}/rest/v1/quizzes",
            json={"id": quiz_id, "questions": questions, "answers": answers},
            headers={
                "apikey": service_role,
                "Authorization": f"Bearer {service_role}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            timeout=10,
        )
        if r.status_code in (200, 201):
            print(f"INFO: Quiz {quiz_id} saved to Supabase.")
        else:
            print(f"WARN: Supabase returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"WARN: Could not save quiz to Supabase: {e}")


def safe_generate_today():
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

    # Pick 5 grade levels to feature today, cycling so all 12 grades appear across the fortnight.
    # Day-of-year offset ensures a different mix each day.
    _all_grades = ["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12"]
    _doy = datetime.date.today().timetuple().tm_yday
    _featured = [_all_grades[(_doy + i * 3) % 12] for i in range(5)]
    featured_grades_str = ", ".join(_featured)

    grade_curriculum = """
CANADIAN MATH CURRICULUM GUIDE — use this to calibrate each problem:
  G1 (Grade 1): counting to 100, addition/subtraction within 20, skip counting by 2s/5s/10s, comparing numbers, coin recognition (pennies/nickels/dimes)
  G2 (Grade 2): addition/subtraction within 100, telling time (hour/half-hour), measuring length (cm/m), simple patterns, counting coins to $1
  G3 (Grade 3): multiplication tables (2,3,4,5,10), basic division, fractions (1/2,1/3,1/4), perimeter of simple shapes, reading simple graphs
  G4 (Grade 4): all multiplication tables to 9×9, long division with remainders, decimal place value (tenths/hundredths), comparing fractions, area of rectangles, elapsed time
  G5 (Grade 5): multi-digit multiplication/division, adding/subtracting fractions with like denominators, decimal operations, percentage intro (50%, 25%, 10%), volume of rectangular prism
  G6 (Grade 6): fraction multiplication/division, ratios and rates, percent of a number, integers intro (positive/negative), order of operations (BEDMAS), simple algebraic expressions
  G7 (Grade 7): integer operations (all four), fraction and decimal fluency, percentage problems (discount/tax/tip), one-step linear equations, surface area, data/probability
  G8 (Grade 8): two-step linear equations, square roots and perfect squares, Pythagorean theorem (simple), percent increase/decrease, slope intro, mean/median/mode
  G9 (Grade 9): linear equations and inequalities, polynomials (add/subtract/multiply), graphing lines (slope-intercept), similar triangles, trigonometry intro (SOH-CAH-TOA), statistics
  G10 (Grade 10): quadratic equations (factoring, completing the square), systems of equations, circle geometry, trigonometry (all ratios), surface area and volume of 3D shapes
  G11 (Grade 11): functions (linear/quadratic/exponential), logarithms intro, sequences and series, financial math (compound interest, annuities), trigonometric identities
  G12 (Grade 12): advanced functions (polynomial/rational/trig), derivatives intro (rates of change), combinations and permutations, vectors intro, probability distributions"""

    prompt = f"""
You are creating today's daily math problems for Canadian students in Grades 1–12.
Today's featured grades are: {featured_grades_str}.
Generate exactly 5 problems — one per featured grade in the order listed above.

{grade_curriculum}

RULES for each problem:
- The problem MUST match the curriculum topics for its assigned grade exactly.
- Use only concepts a student AT that grade would have learned. Do NOT include topics above their grade.
- Use real-life Canadian contexts: loonies/toonies, hockey, maple syrup, Tim Hortons, snowfall (cm), camping, school supplies priced in CAD.
- The Answer must be a single number (integer or simple decimal). No units in the answer field.
- Keep problem language short, friendly, and age-appropriate.
- Provide the problem in both English and French.

For each problem provide ALL of these fields:
- Title: a short child-friendly name
- EN: problem statement in English
- FR: same problem in French
- Grade Tag: the assigned grade code (e.g. G4, G9, G11)
- Hint: one short hint in English (do not give away the answer)
- Steps: 2–5 bullet steps in English showing how to solve it
- Answer: the final numeric answer only (no units, no words)

Output format — use EXACTLY this Markdown (no deviations):
# Daily Math - {today}
## Problems
1. **Title**
   - EN: ...
   - FR: ...
   - Grade Tag: G1/G2/G3/G4/G5/G6/G7/G8
   - Hint: ...
   - Steps:
     - ...
     - ...
   - Answer: ...
(repeat for problems 2–5)

## Today's Encouragement
One cheerful sentence (10–16 words, English only). No emojis.

## Mini Story of Kindness
A 3–4 sentence story about a child helping someone in Canada (English, very simple language, Grade 3 reading level).
"""

    try:
        resp = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = resp.output_text.strip()
        if not text:
            print("WARN: OpenAI returned empty text; skipping page write.")
            return
        md_path.write_text(text + "\n", encoding="utf-8")

        body_html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])

        # Wrap the problems <ol> with an id so JS can target it
        body_html = body_html.replace('<ol>\n<li>', '<ol id="problems-list">\n<li>', 1)

        # Style the Encouragement section as a callout
        if "<h2>Today's Encouragement</h2>" in body_html:
            parts = body_html.split("<h2>Today's Encouragement</h2>", 1)
            if "<p>" in parts[1]:
                parts[1] = parts[1].replace("<p>", '<blockquote class="encouragement"><p>', 1)\
                                   .replace("</p>", "</p></blockquote>", 1)
                body_html = "<h2>Today's Encouragement</h2>".join(parts)

        page_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{TITLE} - {today}</title><link rel="stylesheet" href="../styles.css"/></head>
<body>
<header>
  <a href="../index.html">🧮 {TITLE}</a>
  <span class="user-badge"></span>
</header>
<main class="container">
<div id="review-section"></div>
{body_html}
<div id="reminder-btn-wrap" style="margin:12px 0"></div>
<div id="quiz-feelings"></div>
<section class="hero" id="quiz-box">
  <h2>Test Yourself! 📝</h2>
  <p id="hello">Enter your answers below — your score is saved and you earn points!</p>
  <form id="quiz" aria-label="Enter answers">
    <ol>
      <li><input name="q1" placeholder="Answer 1" required autocomplete="off"></li>
      <li><input name="q2" placeholder="Answer 2" required autocomplete="off"></li>
      <li><input name="q3" placeholder="Answer 3" required autocomplete="off"></li>
      <li><input name="q4" placeholder="Answer 4" required autocomplete="off"></li>
      <li><input name="q5" placeholder="Answer 5" required autocomplete="off"></li>
    </ol>
    <button type="submit">Submit &amp; Earn Points 🌟</button>
  </form>
  <p id="result"></p>
  <p id="streak-msg" style="margin-top:8px;font-size:.95rem;color:var(--muted)"></p>
</section>
<p class="back"><a href="../index.html">← Back to Home</a></p>
</main>
<footer>© {datetime.date.today().year} • Free math practice for kids • Moncton, NB</footer>
<script>
  window.DMK_API  = '{PUBLIC_API}';
  window.DMK_ROOT = '../';
</script>
<script src="../scripts/app.js"></script>
<script>
  const QUIZ_ID = '{today}';
  document.addEventListener('DOMContentLoaded', () => {{
    renderFeelingsCheckin('quiz-feelings');
    renderReviewSection('review-section');
    renderReminderButton('reminder-btn-wrap');
  }});
  document.getElementById('quiz').addEventListener('submit', async function(e) {{
    e.preventDefault();
    const fd = new FormData(this);
    const answers = ['q1','q2','q3','q4','q5'].map(k => fd.get(k).trim());
    const resultEl = document.getElementById('result');
    resultEl.textContent = 'Checking\u2026';
    const ok = await submitQuizAnswers(QUIZ_ID, answers, resultEl);
    if (ok) {{
      markDayDone(QUIZ_ID);
      const streak = calcStreak(QUIZ_ID);
      const streakEl = document.getElementById('streak-msg');
      streakEl.textContent = streak > 1
        ? '\uD83D\uDD25 ' + streak + '-day streak! Keep it up!'
        : '\u2B50 Day 1 \u2014 great start!';
    }}
  }});
</script>
{HELPERS_JS}
</body></html>"""
        html_path.write_text(page_html, encoding="utf-8")
        print(f"INFO: Wrote {html_path}")

        questions = re.findall(r'^\s*-\s*EN:\s*(.+)', text, re.MULTILINE)
        answers   = re.findall(r'^\s*-\s*Answer:\s*(\S+)', text, re.MULTILINE)
        upsert_quiz_to_supabase(today, questions, answers)
    except Exception as e:
        print(f"ERROR: OpenAI generation failed: {e}", file=sys.stderr)

def rebuild_index_and_sitemap():
    pages = sorted(DAILY_DIR.glob("*.html"), key=lambda p: p.name, reverse=True)
    latest = pages[0].stem if pages else None
    today_link = f"daily/{latest}.html" if latest else None
    latest_link_html = (
        f"<a href='{today_link}'>Open today's problems</a>"
        if today_link else "First problems arrive after the first daily run."
    )
    recent_items = (
        "".join(f'<li><a href="daily/{p.name}">Daily Math - {p.stem}</a></li>' for p in pages[:30])
        if pages else "<li>No daily pages yet.</li>"
    )

    index_html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{TITLE} – Free Practice for Moncton Students</title>
  <meta name="description" content="Free daily math practice for kids in Grades 1–8. Earn points, build streaks, and see your ranking!"/>
  <link rel="stylesheet" href="styles.css"/>
</head>
<body>
  <header>
    <a href="index.html">🧮 {TITLE}</a>
    <span class="user-badge"></span>
  </header>
  <main class="container">
    <section class="hero">
      <h1>Practice a little every day</h1>
      <p>Five kid-friendly math problems posted daily — aligned to the Canadian curriculum. Simple, positive, and <strong>free</strong>.</p>
      <p><strong>Latest:</strong> {latest_link_html}</p>
      <p id="join-cta" style="margin-top:10px">
        <button onclick="showRegModal()" style="font-size:1rem;padding:12px 22px">Join Free &amp; Track Your Progress 🚀</button>
      </p>
    </section>
    <div class="points-info">
      🌟 <strong>How points work:</strong> Complete a daily quiz to earn points — 1 point per correct answer, +3 bonus for a perfect score!
      Check the <a href="leaderboard.html">🏆 Rankings</a> to see where you stand.
    </div>
    <section>
      <h2>Recent days</h2>
      <ul class="list">
        {recent_items}
      </ul>
    </section>
    <section style="margin-top:28px">
      <h2>About this site</h2>
      <p>Built with ❤️ for kids in <strong>Moncton, NB, Canada</strong> (and anywhere else!). Daily problems cover
         addition, subtraction, multiplication, division, and word problems across Grades 1–8.</p>
      <p>A Sunday tutoring session is also available — check back for details!</p>
    </section>
  </main>
  <footer>© {datetime.date.today().year} • Free math practice for kids • Moncton, NB</footer>
  <script>
    window.DMK_API  = '{PUBLIC_API}';
    window.DMK_ROOT = './';
  </script>
  <script src="scripts/app.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const u = getUser();
      if (u) document.getElementById('join-cta').style.display = 'none';
    }});
  </script>
</body></html>"""
    (ROOT / "index.html").write_text(index_html, encoding="utf-8")

    repo = os.getenv("GITHUB_REPOSITORY", "YOUR_USERNAME/dailymathforkids")
    user, repo_name = (repo.split("/", 1) + [""])[:2]
    base_url = f"https://{user}.github.io/{repo_name}/"
    urls = (
        [base_url, base_url + "leaderboard.html"]
        + [base_url + f"daily/{p.name}" for p in sorted(DAILY_DIR.glob("*.html"))]
    )
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc></url>" for u in urls]
    sitemap.append("</urlset>\n")
    (ROOT / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    print("INFO: Rebuilt index.html and sitemap.xml")

if __name__ == "__main__":
    safe_generate_today()
    rebuild_index_and_sitemap()
