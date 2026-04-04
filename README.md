# Daily Math for Kids

A free website that publishes **5 new math problems every day** for Grades 1–12,
powered by AI. Kids can register, submit answers, earn points, and see their rankings on a
live leaderboard. Built with ❤️ for students in Moncton, NB, Canada (and anywhere else!).

## Live Site
- GitHub Pages URL (after enabling Pages): `https://YOUR_USERNAME.github.io/dailymathforkids`

## Features
- 5 fresh problems every day covering Grades 1–12 (Canadian curriculum contexts)
- English & French bilingual problems with TTS read-aloud buttons
- Hints, step-by-step guidance, and answer reveal for each problem
- Grade-level difficulty filter (kids choose their grade)
- **Student registration** — nickname, grade, school, city
- **Points system** — 1 pt per correct answer + 3 bonus for a perfect score
- **Live leaderboard** — filterable by grade and city
- **Daily streaks** tracked in the browser
- Fully automated daily content — no human intervention needed
- Positive & encouraging tone throughout

## How it Works
1. A GitHub Action runs every morning and calls ChatGPT to generate 5 grade-tagged problems.
2. Problems + answers are saved as HTML in `/daily` and uploaded to Supabase as a quiz record.
3. GitHub Pages serves the static site; Vercel hosts the serverless API.
4. Kids visit the site, register once, solve problems, and submit answers to earn points.

## Quick Start

### 1. Deploy the API (Vercel + Supabase)
See `dailymathforkids-api` repo for full instructions. In short:
- Create a free [Supabase](https://supabase.com) project and run `schema.sql` in the SQL editor.
- Deploy the API folder to [Vercel](https://vercel.com) and set these environment variables:
  - `SUPABASE_URL` — from Supabase project settings
  - `SUPABASE_SERVICE_ROLE` — service role secret key

### 2. Set the API URL in the frontend
Replace `https://YOUR_BACKEND_URL` with your actual Vercel deployment URL in:
- `index.html`
- `leaderboard.html`
- `daily/*.html` (auto-set by `scripts/gen_site.py` via `PUBLIC_API_BASE` env var)

### 3. Configure GitHub Actions secrets
- `OPENAI_API_KEY` — for daily problem generation
- `PUBLIC_API_BASE` — your Vercel API URL (e.g. `https://myapi.vercel.app`)

### 4. Enable GitHub Pages
- Repo → Settings → Pages → Branch: `main`, Folder: `/ (root)`

### 5. Run the first generation
- Repo → Actions → Daily Math → Run workflow

## Points System
| Action | Points |
|--------|--------|
| Each correct answer | +1 pt |
| Perfect score (5/5) | +3 bonus pts |
| Maximum per quiz | 8 pts |

## Notes
- **Time zone:** Workflow runs at 07:00 America/Moncton (10:00 UTC). Adjust cron in `.github/workflows/daily.yml`.
- **Cost:** Using `gpt-4o-mini` costs only a few cents per month.
- **Grades:** Problems cover G1–G12; 5 grades are featured each day, cycling so all grades appear regularly.
- **Tutoring:** Free in-person sessions in Moncton for Grades 3–8 (expanding to Grade 12 in future).
- **No passwords:** Students identify by nickname only — simple and kid-friendly.

## License
- Content: CC BY 4.0
