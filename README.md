# Daily Math for Kids

A free website that publishes **5 new kid-friendly math problems with answers every day**, powered by AI.
The goal is to help kids build confidence in math through short, daily practice.

## Live Site
- GitHub Pages URL (after enabling Pages): `https://YOUR_USERNAME.github.io/dailymathforkids`

## Features
- 5 fresh problems every day (add, subtract, multiply, divide, simple word problem)
- Answers included so kids can check themselves
- Positive & encouraging tone
- Recent days archive
- Fully automated – no human intervention needed

## How it Works
1. A script asks ChatGPT to create 5 new math problems daily.
2. Problems + answers are saved as Markdown & HTML in `/daily`.
3. GitHub Actions commits the new page each morning.
4. The website updates itself.

## Quick Start
1. Add your OpenAI API key as a GitHub Actions secret named `OPENAI_API_KEY`:
   - Repo → Settings → Secrets and variables → Actions → New repository secret → `OPENAI_API_KEY`
2. Enable GitHub Pages:
   - Repo → Settings → Pages → Branch: `main`, Folder: `/ (root)`
3. Run the workflow once manually:
   - Repo → Actions → Daily Math → Run workflow

## Notes
- Time zone: The workflow is scheduled to run at 07:00 America/Moncton (10:00 UTC). Adjust cron in `.github/workflows/daily.yml` if needed.
- Cost: Using `gpt-4o-mini`, this should cost only a few cents per month.
- Customize difficulty: Edit the prompt in `scripts/gen_site.py`.

## License
- Content: CC BY 4.0
