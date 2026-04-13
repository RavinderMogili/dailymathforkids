import os, pathlib, datetime, sys, re
import markdown2

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

ROOT = pathlib.Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "daily"
DAILY_DIR.mkdir(parents=True, exist_ok=True)

TITLE       = os.getenv("SITE_TITLE", "Daily Math for Kids")
PUBLIC_API  = os.getenv("PUBLIC_API_BASE", "https://YOUR_BACKEND_URL").rstrip("/")
GRADE_CODES = ["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12"]

HELPERS_JS = r"""
<script>
(function enhanceProblems() {
  document.querySelectorAll('.problems-list > li').forEach(li => {
    const text = li.innerText;
    const en      = (text.match(/EN:\s*([\s\S]*?)(?=\n\s*FR:)/i)       || [])[1]?.trim() || '';
    const fr      = (text.match(/FR:\s*([\s\S]*?)(?=\n\s*Choices:)/i)  || [])[1]?.trim() || '';
    const choiceStr = (text.match(/Choices:\s*([^\n]+)/i)              || [])[1]?.trim() || '';
    const hint    = (text.match(/Hint:\s*([\s\S]*?)(?=\n\s*Steps:)/i)  || [])[1]?.trim() || '';
    const steps   = (text.match(/Steps:\s*([\s\S]*?)(?=\n\s*Answer:)/i)|| [])[1]?.trim() || '';
    const ans     = (text.match(/Answer:\s*(\S+)/i)                    || [])[1]?.trim() || '';

    const choiceParts = choiceStr.split(/\s{2,}(?=[A-D]\))/i);
    const choicePairs = choiceParts.map(p => {
      const m = p.match(/^([A-D])\)\s*(.+)/i);
      return m ? { label: m[1].toUpperCase(), value: m[2].trim() } : null;
    }).filter(Boolean);

    li.dataset.answer   = ans;
    li.dataset.question  = en;

    const titleMatch = li.innerHTML.match(/<strong>(.*?)<\/strong>/);
    const titleHtml  = titleMatch ? '<strong>' + titleMatch[1] + '</strong>' : '';

    function speak(t, lang) {
      const u = new SpeechSynthesisUtterance(t);
      u.lang = lang; u.rate = 0.95; u.pitch = 1.05;
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    }

    const stepsHtml = steps
      ? '<ul style="margin:4px 0;padding-left:20px"><li>' + steps.replace(/\n\s*-\s*/g, '</li><li>') + '</li></ul>'
      : '';

    const tag = li.closest('.grade-section')?.dataset.grade || '';
    const bar = document.createElement('div');
    bar.style.cssText = 'margin:8px 0;display:flex;flex-wrap:wrap;gap:6px;align-items:flex-start';
    bar.innerHTML =
      '<button type="button" class="tts-en" style="min-height:32px;padding:4px 10px;font-size:.82rem">&#127911; Listen EN</button>' +
      '<button type="button" class="tts-fr" style="min-height:32px;padding:4px 10px;font-size:.82rem">&#127911; Listen FR</button>' +
      (hint ? '<details style="width:100%;margin-top:4px"><summary style="cursor:pointer;font-weight:700;color:var(--warn)">&#128161; Show hint</summary><p style="margin:6px 0 0;padding:8px;background:var(--warn-light);border-radius:8px">' + hint + '</p></details>' : '') +
      (stepsHtml ? '<details style="width:100%;margin-top:4px"><summary style="cursor:pointer;font-weight:700;color:var(--primary)">&#128218; Show steps</summary>' + stepsHtml + '</details>' : '');

    const choicesHtml = choicePairs.length
      ? '<div class="mc-options" style="display:flex;flex-wrap:wrap;gap:8px;margin:10px 0">' +
        choicePairs.map(c =>
          '<button type="button" class="mc-btn" data-value="' + c.value + '"' +
          ' style="min-height:40px;padding:8px 18px;background:var(--surface);color:var(--ink);' +
          'border:2px solid var(--border);border-radius:var(--radius-pill);cursor:pointer;font-family:inherit;font-size:.95rem;font-weight:600">' +
          '<span style="color:var(--primary);font-weight:800">' + c.label + ')</span> ' + c.value +
          '</button>'
        ).join('') + '</div>'
      : '';

    li.innerHTML = titleHtml + '<p style="margin:6px 0 4px">' + (en || '') + '</p>' + choicesHtml;

    li.querySelectorAll('.mc-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        li.querySelectorAll('.mc-btn').forEach(b => {
          b.style.background = 'var(--surface)';
          b.style.borderColor = 'var(--border)';
          b.style.color = 'var(--ink)';
        });
        btn.style.background  = 'var(--primary)';
        btn.style.borderColor = 'var(--primary)';
        btn.style.color       = '#fff';
        li.dataset.selected   = btn.dataset.value;
      });
    });

    li.appendChild(bar);

    bar.querySelector('.tts-en').onclick = () => speak(en, 'en-CA');
    bar.querySelector('.tts-fr').onclick = () => speak(fr, 'fr-CA');
  });
})();

</script>
"""

def parse_grade_sections(text):
    sections = {}
    for code in GRADE_CODES:
        m = re.search(rf'## {re.escape(code)}\n(.*?)(?=\n## |\Z)', text, re.DOTALL)
        if m:
            sections[code] = m.group(1).strip()
    return sections


def upsert_quiz_to_supabase(quiz_id, questions, answers):
    api_base     = os.environ.get("PUBLIC_API_BASE", "").strip().rstrip("/")
    service_role = os.environ.get("SUPABASE_SERVICE_ROLE", "").strip()
    if not api_base or not service_role:
        print("INFO: API/service-role env vars not set — skipping quiz DB insert.")
        return
    try:
        import httpx
        r = httpx.post(
            f"{api_base}/api/upsert-quiz",
            json={"quizId": quiz_id, "questions": questions, "answers": answers},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {service_role}",
            },
            timeout=15,
        )
        if r.status_code == 200:
            print(f"INFO: Quiz {quiz_id} saved via API.")
        else:
            print(f"WARN: upsert-quiz returned {r.status_code}: {r.text}")
    except Exception as e:
        print(f"WARN: Could not save quiz {quiz_id}: {e}")


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

    if html_path.exists() and html_path.stat().st_size > 1000:
        print(f"INFO: {html_path.name} already exists ({html_path.stat().st_size} bytes) — skipping OpenAI generation.")
        if md_path.exists():
            text = md_path.read_text(encoding="utf-8")
            grade_sections = parse_grade_sections(text)
            for code in GRADE_CODES:
                content = grade_sections.get(code, "")
                if content:
                    qs  = re.findall(r'^\s*-\s*EN:\s*(.+)',      content, re.MULTILINE)
                    ans = re.findall(r'^\s*-\s*Answer:\s*(\S+)', content, re.MULTILINE)
                    upsert_quiz_to_supabase(f"{today}-{code}", qs, ans)
        rebuild_index_and_sitemap()
        return

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

    prompt = f"""You are creating daily math problems for Canadian students in Grades 1–12.
Generate exactly 5 problems for EACH grade from G1 to G12. That is 60 problems total.
"""
    prompt += grade_curriculum
    prompt += f"""

RULES:
- Each problem must match the curriculum exactly for its assigned grade. No topics above grade level.
- Use real-life Canadian contexts: loonies/toonies, hockey, maple syrup, Tim Hortons, snowfall (cm), camping, school supplies in CAD.
- Answer must be a single number (integer or simple decimal). No units in the answer field.
- Keep language short, friendly, and age-appropriate.
- Provide each problem in both English and French.

Use EXACTLY this format — no deviations:

# Daily Math - {today}

## G1
1. **Title**
   - EN: problem in English
   - FR: same problem in French
   - Choices: A) [wrong]  B) [correct]  C) [wrong]  D) [wrong]
   - Hint: one short hint (do not give away the answer)
   - Steps:
     - step 1
     - step 2
   - Answer: [number only — must match one of the Choices values exactly]
2. **Title**
   ...
[problems 3-5 for G1]

## G2
[5 problems]

## G3
[5 problems]

## G4
[5 problems]

## G5
[5 problems]

## G6
[5 problems]

## G7
[5 problems]

## G8
[5 problems]

## G9
[5 problems]

## G10
[5 problems]

## G11
[5 problems]

## G12
[5 problems]

## Today's Encouragement
One cheerful sentence (10–16 words, English only). No emojis.

## Mini Story of Kindness
A 3–4 sentence story about a child helping someone in Canada (English, Grade 3 reading level).
"""
    # (original prompt replaced — keep variable name for compatibility)
    _unused_prompt = f"""
"""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8000,
        )
        text = resp.choices[0].message.content.strip()
        if not text:
            print("WARN: OpenAI returned empty text; skipping page write.")
            return
        md_path.write_text(text + "\n", encoding="utf-8")

        page_html = generate_html_from_text(text, today)
        html_path.write_text(page_html, encoding="utf-8")
        print(f"INFO: Wrote {html_path}")

        grade_sections = parse_grade_sections(text)
        for code in GRADE_CODES:
            content = grade_sections.get(code, "")
            if content:
                qs  = re.findall(r'^\s*-\s*EN:\s*(.+)',      content, re.MULTILINE)
                ans = re.findall(r'^\s*-\s*Answer:\s*(\S+)', content, re.MULTILINE)
                upsert_quiz_to_supabase(f"{today}-{code}", qs, ans)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR: generation failed: {e}", file=sys.stderr)
        sys.exit(1)

def generate_html_from_text(text, today):
    grade_sections = parse_grade_sections(text)
    enc_m    = re.search(r"## Today's Encouragement\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    enc_text = enc_m.group(1).strip() if enc_m else "Every problem you solve makes your brain stronger."
    story_m  = re.search(r"## Mini Story of Kindness\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    story_text = story_m.group(1).strip() if story_m else ""

    all_sections_html = ""
    for code in GRADE_CODES:
        content = grade_sections.get(code, "")
        if not content:
            continue
        sec_html = markdown2.markdown(content, extras=["tables", "fenced-code-blocks"])
        sec_html = sec_html.replace('<ol>\n<li>', '<ol class="problems-list">\n<li>', 1)
        grade_num = code[1:]
        all_sections_html += (
            f'\n<div class="grade-section" data-grade="{code}" style="display:none">'
            f'\n<h2>Grade {grade_num} Problems</h2>\n{sec_html}\n</div>\n'
        )

    enc_html   = f'<h2>Today\'s Encouragement</h2>\n<blockquote class="encouragement"><p>{enc_text}</p></blockquote>'
    story_html = f'<h2>A Story of Kindness</h2>\n{markdown2.markdown(story_text)}' if story_text else ""

    page_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{TITLE} - {today}</title><link rel="stylesheet" href="../styles.css"/></head>
<body>
<header>
  <a href="../index.html">&#129518; {TITLE}</a>
  <span class="user-badge"></span>
</header>
<main class="container">
<h1>Daily Math &#8212; {today}</h1>
<div id="review-section"></div>
{all_sections_html}
{enc_html}
{story_html}
<div id="reminder-btn-wrap" style="margin:12px 0"></div>
<div id="corrective-feedback" style="margin:16px 0"></div>
<div id="quiz-feelings"></div>
<section class="hero" id="quiz-box">
  <h2>Test Yourself! &#128221;</h2>
  <div id="quiz-timer" style="display:none;font-size:1.1rem;font-weight:700;color:var(--primary);margin-bottom:8px">&#9201; <span id="timer-display">0:00</span></div>
  <p id="hello">Log in and select your grade &#8212; problems will appear above!</p>
  <form id="quiz" aria-label="Enter answers">
    <ol>
      <li style="display:none"><input name="q1" type="hidden"></li>
      <li style="display:none"><input name="q2" type="hidden"></li>
      <li style="display:none"><input name="q3" type="hidden"></li>
      <li style="display:none"><input name="q4" type="hidden"></li>
      <li style="display:none"><input name="q5" type="hidden"></li>
    </ol>
    <button type="submit">Submit &amp; Earn Points &#127775;</button>
  </form>
  <p id="result"></p>
  <p id="streak-msg" style="margin-top:8px;font-size:.95rem;color:var(--muted)"></p>
</section>
<p class="back"><a href="../index.html">&#8592; Back to Home</a> &nbsp;&middot;&nbsp; <a href="../profile.html">&#128202; My Progress</a> &nbsp;&middot;&nbsp; <a href="../leaderboard.html">&#127942; Rankings</a></p>
</main>
<footer>&#169; {datetime.date.today().year} &#8226; Free math practice for kids &#8226; Moncton, NB</footer>
<script>
  window.DMK_API  = '{PUBLIC_API}';
  window.DMK_ROOT = '../';
</script>
<script src="../scripts/app.js"></script>
<script src="../scripts/goals.js"></script>
<script>
  const QUIZ_DATE = '{today}';
  let QUIZ_ID = QUIZ_DATE + '-G3';
  let _timerTick = null;
  function _startTimerUI() {{
    const timerEl = document.getElementById('quiz-timer');
    const dispEl  = document.getElementById('timer-display');
    if (!timerEl || !dispEl) return;
    dmkTimer.begin();
    timerEl.style.display = 'block';
    if (_timerTick) return;
    _timerTick = setInterval(() => {{
      dispEl.textContent = dmkTimer.fmt(dmkTimer.elapsed());
    }}, 1000);
  }}
  document.addEventListener('DOMContentLoaded', () => {{
    showGradeProblems();
    renderFeelingsCheckin('quiz-feelings');
    renderReviewSection('review-section');
    renderReminderButton('reminder-btn-wrap');
    document.addEventListener('click', function _startClick(e) {{
      if (e.target.closest('#start-test-btn')) {{ startTest(); document.removeEventListener('click', _startClick); }}
    }});
  }});
  document.getElementById('quiz').addEventListener('submit', async function(e) {{
    e.preventDefault();
    const grade = (window.QUIZ_ID || QUIZ_ID).replace(/^.*-(G\d+)$/, '$1');
    const section = document.querySelector('.grade-section[data-grade="' + grade + '"]');
    const lis = section ? section.querySelectorAll('.problems-list > li') : [];
    ['q1','q2','q3','q4','q5'].forEach((k, i) => {{
      const sel = lis[i] ? (lis[i].dataset.selected || '') : '';
      const input = document.querySelector('input[name="' + k + '"]');
      if (input) input.value = sel;
    }});
    const answers = ['q1','q2','q3','q4','q5'].map(k => {{
      const inp = document.querySelector('input[name="' + k + '"]');
      return inp ? inp.value.trim() : '';
    }});
    const resultEl = document.getElementById('result');
    resultEl.textContent = 'Checking\u2026';
    const qid = window.QUIZ_ID || QUIZ_ID;
    const secs = dmkTimer.stop();
    const timerEl = document.getElementById('quiz-timer');
    if (timerEl) timerEl.style.display = 'none';
    const ok = await submitQuizAnswers(qid, answers, resultEl, secs || null);
    if (ok) {{
      dmkTimer.reset();
      markDayDone(qid);
      const streak = calcStreak(qid);
      const streakEl = document.getElementById('streak-msg');
      streakEl.textContent = streak > 1
        ? '\U0001F525 ' + streak + '-day streak! Keep it up!'
        : '\u2B50 Day 1 \u2014 great start!';

      const grade = qid.replace(/^.*-(G\d+)$/, '$1');
      const section = document.querySelector('.grade-section[data-grade="' + grade + '"]');
      const feedbackEl = document.getElementById('corrective-feedback');
      if (section && feedbackEl) {{
        const lis = section.querySelectorAll('.problems-list > li');
        let html = '<h3 style="margin-bottom:10px">Your Results</h3><ol style="list-style:none;padding:0;margin:0">';
        answers.forEach((userAns, i) => {{
          const li = lis[i];
          const correct = li ? (li.dataset.answer || '').trim() : '';
          const q = li ? (li.dataset.question || '') : '';
          const isRight = userAns.trim().toLowerCase() === correct.toLowerCase();
          html += '<li style="margin:8px 0;padding:10px 14px;border-radius:10px;background:' +
            (isRight ? 'var(--success-light)' : 'var(--danger-light)') + ';border:1px solid ' +
            (isRight ? 'var(--success)' : 'var(--danger)') + '">';
          html += (isRight ? '&#9989;' : '&#10060;') + ' <strong>Q' + (i+1) + ':</strong> ' + (q || '(question ' + (i+1) + ')') + '<br>';
          html += 'Your answer: <strong>' + (userAns || '—') + '</strong>';
          if (!isRight) html += ' &nbsp;&middot;&nbsp; Correct: <strong style="color:var(--success)">' + (correct || '?') + '</strong>';
          html += '</li>';
        }});
        html += '</ol>';
        feedbackEl.innerHTML = html;
        feedbackEl.scrollIntoView({{behavior:'smooth', block:'nearest'}});
      }}
    }}
  }});
</script>
{HELPERS_JS}
</body></html>"""
    return page_html

def rebuild_index_and_sitemap():
    pages = sorted(
        [p for p in DAILY_DIR.glob("*.html") if re.match(r'\d{4}-\d{2}-\d{2}\.html$', p.name)],
        key=lambda p: p.name, reverse=True
    )
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
      <p>Five math problems posted daily across <strong>Grades 1–12</strong> — aligned to the Canadian curriculum. Simple, positive, and <strong>free</strong>.</p>
      <p id="latest-link"><strong>Latest:</strong> {latest_link_html}</p>
      <p id="join-cta" style="margin-top:10px">
        <button onclick="showRegModal()" style="font-size:1rem;padding:12px 22px">Join Free &amp; Track Your Progress 🚀</button>
      </p>
    </section>
    <div class="points-info">
      🌟 <strong>How points work:</strong> Complete a daily quiz to earn points — 1 point per correct answer, +3 bonus for a perfect score!
      Check the <a href="leaderboard.html">🏆 Rankings</a> or <a href="profile.html">📊 My Progress</a> to see how you're doing.
    </div>
    <div id="weekly-goal-home"></div>
    <div style="margin:12px 0" id="reminder-btn-wrap"></div>
    <section>
      <h2>Recent days</h2>
      <ul class="list">
        {recent_items}
      </ul>
    </section>
    <section style="margin-top:28px">
      <h2>About this site</h2>
      <p>Built with ❤️ for kids in <strong>Moncton, NB, Canada</strong> (and anywhere else!). Daily problems cover
         all topics from Grades 1–12 — generated fresh every day.</p>
    </section>
  </main>
  <footer>© {datetime.date.today().year} • Free math practice for kids • Moncton, NB</footer>
  <script>
    window.DMK_API  = '{PUBLIC_API}';
    window.DMK_ROOT = './';
  </script>
  <script src="scripts/app.js"></script>
  <script src="scripts/goals.js"></script>
  <script>
    document.addEventListener('DOMContentLoaded', () => {{
      const u = getUser();
      if (u) document.getElementById('join-cta').style.display = 'none';
      renderWeeklyGoalWidget('weekly-goal-home');
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
