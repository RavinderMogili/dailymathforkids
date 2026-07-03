# Daily Math for Kids

A free website that publishes **new math problems every day** for Grades 1–12.
Kids can register, solve daily quizzes, practice by topic, earn points and badges,
and track their progress. Built with ❤️ for students in Moncton, NB, Canada (and anywhere else!).

## Live Site
https://ravindermogili.github.io/dailymathforkids/

## Features
- Fresh problems every day covering Grades 1–12 (Canadian curriculum contexts)
- English & French bilingual problems with read-aloud (TTS) buttons
- Hints and step-by-step guidance for every problem — without giving away the answer
- **Math Helper** — a built-in chat-style guide that helps kids figure out problems themselves
- **Practice Mode** — pick a topic and difficulty, practice anytime
- **Mistake Review** — wrong answers are saved so kids can retry them later
- **Student registration** — nickname, grade, school, city (no email required for kids)
- **Points & badges** — 1 pt per correct answer + bonus for a perfect score
- **Daily streaks and weekly goals** to keep kids motivated
- **My Progress page** — quiz history, points, streaks, and mistake history
- Dark mode, animated math background, and a friendly mascot
- Fully automated daily content — no human intervention needed
- Positive & encouraging tone throughout

## How it Works
1. A GitHub Action runs every morning and calls Claude (Anthropic) to generate grade-tagged problems for all grades. Falls back to OpenAI if needed.
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
Replace the API base URL with your actual Vercel deployment URL in:
- `index.html`
- `practice.html`, `profile.html`
- `daily/*.html` (auto-set by `scripts/gen_site.py` via `PUBLIC_API_BASE` env var)

### 3. Configure GitHub Actions secrets
- `ANTHROPIC_API_KEY` — for daily problem generation (Claude)
- `OPENAI_API_KEY` — optional fallback for generation
- `PUBLIC_API_BASE` — your Vercel API URL (e.g. `https://myapi.vercel.app`)

### 4. Enable GitHub Pages
- Repo → Settings → Pages → Branch: `main`, Folder: `/ (root)`

### 5. Run the first generation
- Repo → Actions → Daily Math → Run workflow

## Points System
| Action | Points |
|--------|--------|
| Each correct answer | +1 pt |
| Perfect score on a quiz | +3 bonus pts |
| Practice sessions | points per correct answer (daily cap) |

## Notes
- **Time zone:** Workflow runs at 07:00 America/Moncton (10:00 UTC). Adjust cron in `.github/workflows/daily.yml`.
- **Cost:** Daily generation with Claude costs only a few cents per day.

## License
- Content: CC BY 4.0
