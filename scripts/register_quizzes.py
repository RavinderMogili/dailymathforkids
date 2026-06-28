"""
Register manually-added quiz grades (G8-G12) in Supabase so submissions work.
One-time script — run once then delete.
"""
import re, os, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
HTML_FILE = ROOT / "daily" / "2026-06-25.html"

API_BASE = os.environ.get("PUBLIC_API_BASE", "https://dailymathforkids-api.vercel.app")
SERVICE_ROLE = os.environ.get("SUPABASE_SERVICE_ROLE", "").strip()

if not SERVICE_ROLE:
    print("ERROR: Set SUPABASE_SERVICE_ROLE env var first.")
    print("  PowerShell: $env:SUPABASE_SERVICE_ROLE = 'your-key-here'")
    sys.exit(1)

html = HTML_FILE.read_text(encoding='utf-8')

# Parse questions and answers from each grade section
grades_to_register = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10', 'G11', 'G12']

import httpx

for grade in grades_to_register:
    pattern = rf'<div class="grade-section" data-grade="{grade}"[^>]*>(.*?)</div>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        print(f"  {grade}: section not found, skipping")
        continue

    section = match.group(1)
    
    # Extract EN questions
    questions = re.findall(r'<li>EN:\s*(.+?)</li>', section)
    # Extract answers
    answers = re.findall(r'<li>Answer:\s*(.+?)</li>', section)

    if not questions or not answers:
        print(f"  {grade}: no questions/answers found, skipping")
        continue

    quiz_id = f"2026-06-25-{grade}"
    print(f"  {grade}: {len(questions)} questions, {len(answers)} answers → registering as {quiz_id}")

    try:
        r = httpx.post(
            f"{API_BASE}/api/upsert-quiz",
            json={"quizId": quiz_id, "questions": questions, "answers": answers},
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SERVICE_ROLE}",
            },
            timeout=15,
        )
        if r.status_code == 200:
            print(f"    [OK] {quiz_id} registered successfully")
        else:
            print(f"    [FAIL] {quiz_id} failed: {r.status_code} -- {r.text}")
    except Exception as e:
        print(f"    [FAIL] {quiz_id} error: {e}")

print("\nDone!")
