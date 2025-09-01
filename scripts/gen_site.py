import os, pathlib, datetime, sys
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

    prompt = f"""
Create 5 math problems for Grades 2–4 (Canada). OUTPUT IN ENGLISH & FRENCH with hints and steps.

For each problem provide:
- A child-friendly Title
- EN: The problem statement (English)
- FR: The same problem (French)
- Grade Tag: G2 or G3 or G4 (pick one appropriate)
- Hint: one short hint (English)
- Steps: 2–5 bullet steps (English) to solve
- Answer: final numeric answer (English)

Keep numbers < 100 and use real-life contexts (money, time, sharing, measurement). Keep language short and friendly.

Formatting (Markdown exactly):
# Daily Math - {today}
## Problems
1. **Title**
   - EN: ...
   - FR: ...
   - Grade Tag: G2/G3/G4
   - Hint: ...
   - Steps:
     - ...
     - ...
   - Answer: ...
(repeat until 5)

## Today's Encouragement
One cheerful sentence (10–16 words, English). No emojis.

## Mini Story of Kindness
A 3–4 sentence story about kindness or humility for kids (English, simple).
"""

    try:
        resp = client.responses.create(model="gpt-4o-mini", input=prompt)
        text = resp.output_text.strip()
        if not text:
            print("WARN: OpenAI returned empty text; skipping page write.")
            return
        md_path.write_text(text + "\n", encoding="utf-8")

        body_html = markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])

        # Style the Encouragement section as a callout
        if "<h2>Today's Encouragement</h2>" in body_html:
            parts = body_html.split("<h2>Today's Encouragement</h2>", 1)
            if "<p>" in parts[1]:
                parts[1] = parts[1].replace("<p>", '<blockquote class="encouragement"><p>', 1)\
                                   .replace("</p>", "</p></blockquote>", 1)
                body_html = "<h2>Today's Encouragement</h2>".join(parts)

        # Inject helper JS (TTS, Hint/Steps/Answer reveal, Streaks, Difficulty filter)
        helpers_js = f"""
<script>
const store={{get:(k,v=null)=>JSON.parse(localStorage.getItem(k)||JSON.stringify(v)),set:(k,v)=>localStorage.setItem(k,JSON.stringify(v))}};
function speak(text,lang='en-CA'){{const u=new SpeechSynthesisUtterance(text);u.lang=lang;u.rate=0.95;u.pitch=1.05;speechSynthesis.cancel();speechSynthesis.speak(u);}}

(function enhanceProblems(){{ 
  document.querySelectorAll('ol > li').forEach((li)=>{{ 
    const text=li.innerText;
    const en=(text.match(/EN:\\s*([\\s\\S]*?)\\n\\s*-\\s*FR:/i)||[])[1]||'';
    const fr=(text.match(/FR:\\s*([\\s\\S]*?)\\n\\s*-\\s*Grade Tag:/i)||[])[1]||'';
    const hint=(text.match(/Hint:\\s*([\\s\\S]*?)\\n\\s*-\\s*Steps:/i)||[])[1]||'';
    const steps=(text.match(/Steps:\\s*([\\s\\S]*?)\\n\\s*-\\s*Answer:/i)||[])[1]||'';
    const ans=(text.match(/Answer:\\s*(.*)$/i)||[])[1]||'';
    const tag=(text.match(/Grade Tag:\\s*(G[234])/i)||[])[1]||'G3';
    const bar=document.createElement('div'); bar.style.margin='8px 0';
    bar.innerHTML=`
      <span style="font-weight:600">Level: ${'{'}tag{'}'}</span>
      <button type="button" class="tts-en" style="margin-left:10px">🎧 EN</button>
      <button type="button" class="tts-fr" style="margin-left:6px">🎧 FR</button>
      <button type="button" class="reveal-hint" style="margin-left:10px">Show hint</button>
      <button type="button" class="reveal-steps" style="margin-left:6px">Show steps</button>
      <button type="button" class="reveal-answer" style="margin-left:6px">Show answer</button>
      <div class="hint" style="display:none;margin:6px 0 0 0;"></div>
      <div class="steps" style="display:none;margin:6px 0 0 0;"></div>
      <div class="answer" style="display:none;margin:6px 0 0 0;font-weight:600;"></div>`;
    li.appendChild(bar);
    bar.querySelector('.tts-en').onclick=()=>speak(en,'en-CA');
    bar.querySelector('.tts-fr').onclick=()=>speak(fr,'fr-CA');
    bar.querySelector('.reveal-hint').onclick=(e)=>{{bar.querySelector('.hint').textContent=hint||'Try drawing or using counters!';bar.querySelector('.hint').style.display='block';e.target.disabled=true;}};
    bar.querySelector('.reveal-steps').onclick=(e)=>{{const s=steps?'<ul><li>'+steps.replace(/\\n\\s*-\\s*/g,'</li><li>')+'</li></ul>':'<ul><li>Break it into smaller parts.</li></ul>';bar.querySelector('.steps').innerHTML=s;bar.querySelector('.steps').style.display='block';e.target.disabled=true;}};
    bar.querySelector('.reveal-answer').onclick=(e)=>{{bar.querySelector('.answer').textContent=ans||'Check your steps!';bar.querySelector('.answer').style.display='block';e.target.disabled=true;}};
    li.dataset.level=tag;
  }});
}})();

(function difficultyFilter(){{ 
  const box=document.createElement('div'); box.className='hero'; box.setAttribute('aria-label','Difficulty');
  box.innerHTML=`<strong>Choose your level:</strong>
    <label style="margin-left:8px"><input type="radio" name="lvl" value="G2"> Grade 2</label>
    <label style="margin-left:8px"><input type="radio" name="lvl" value="G3"> Grade 3</label>
    <label style="margin-left:8px"><input type="radio" name="lvl" value="G4"> Grade 4</label>`;
  const title = document.querySelector('h1');
  if (title) title.after(box);
  const radios=box.querySelectorAll('input[name="lvl"]');
  const saved=store.get('dmk_lvl','G3'); radios.forEach(r=>r.checked=(r.value===saved));
  function apply(){{ const lvl=[...radios].find(r=>r.checked)?.value||'G3';
    store.set('dmk_lvl',lvl);
    document.querySelectorAll('ol > li').forEach(li=>{{ li.style.opacity=(li.dataset.level===lvl)?'1':'0.45'; }});
  }}
  radios.forEach(r=>r.addEventListener('change',apply)); apply();
}})();

(function streaks(){{
  const today=location.pathname.split('/').pop().replace('.html','');
  const doneDays=store.get('doneDays',{{}});
  const badge=document.createElement('p'); badge.style.fontWeight='600';
  const main=document.querySelector('main'); if (main) main.prepend(badge);
  function calcStreak(map){{ const days=Object.keys(map).filter(k=>map[k]).sort(); if(!days.length) return 0; let s=0; const d=new Date(today); for(;;){{ const ymd=d.toISOString().slice(0,10); if(map[ymd]){{s++; d.setDate(d.getDate()-1);}} else break; }} return s; }}
  const result=document.getElementById('result'); const orig=(result.textContent if result else '');
  function markDone(scoreText=''){{ doneDays[today]=True; store.set('doneDays',doneDays); const s=calcStreak(doneDays); badge.textContent=`⭐ Great job! Current streak: ${'{'}s{'}'} day${'{'}s===1?'':'s'{'}'}.`; if(result) result.textContent = scoreText or orig or 'Done for today ✅'; }}
  const quiz=document.getElementById('quiz'); if(quiz){{ quiz.addEventListener('submit', function(e){{ setTimeout(()=>{{ markDone(result?result.textContent:''); }}, 120); }}); }}
}})();
</script>
"""
        page_html = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{TITLE} - {today}</title><link rel="stylesheet" href="../styles.css"/></head>
<body>
<header><a href="../index.html">{TITLE}</a></header>
<main class="container">
{body_html}
<section class="hero" id="quiz-box">
  <h2>Mark Today as Done</h2>
  <p id="hello">Enter your answers below to practice and mark today as complete.</p>
  <form id="quiz" aria-label="Enter answers">
    <ol>
      <li><input name="q1" placeholder="Answer 1" required></li>
      <li><input name="q2" placeholder="Answer 2" required></li>
      <li><input name="q3" placeholder="Answer 3" required></li>
      <li><input name="q4" placeholder="Answer 4" required></li>
      <li><input name="q5" placeholder="Answer 5" required></li>
    </ol>
    <button type="submit">Submit & Mark Done</button>
  </form>
  <p id="result"></p>
</section>
<p class="back"><a href="../index.html"><- Back to Home</a></p>
</main>
<footer>© {datetime.date.today().year} • Auto-generated daily</footer>
{helpers_js}
</body></html>"""
        html_path.write_text(page_html, encoding="utf-8")
        print(f"INFO: Wrote {html_path}")
    except Exception as e:
        print(f"ERROR: OpenAI generation failed: {e}", file=sys.stderr)

def rebuild_index_and_sitemap():
    pages = sorted(DAILY_DIR.glob("*.html"), key=lambda p: p.name, reverse=True)
    latest = pages[0].stem if pages else None
    today_link = f"daily/{latest}.html" if latest else None

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
      <p><strong>Latest:</strong> {("<a href='"+today_link+"'>Open today</a>" if today_link else "First post arrives after the first daily run.")}</p>
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
