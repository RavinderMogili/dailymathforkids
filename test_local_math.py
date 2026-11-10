"""Test local llama.cpp Qwen3-8B as a question generator for Daily Math.

Generates a small batch (2 questions x 3 grades) through the local
OpenAI-compatible endpoint, then validates JSON structure, answer-in-choices,
and schema fields. Run the server first via D:\\LocalAI\\llama\\Start-Qwen.bat.
"""

import json
import re
import sys

from openai import OpenAI

LOCAL_URL = "http://127.0.0.1:8080/v1"
LOCAL_MODEL = "Qwen3-8B-Q4_K_M"
GRADES = (3, 6, 9)
QUESTIONS_PER_GRADE = 2

PROMPT = """Generate practice math questions for Canadian students.

Generate exactly {n} questions each for grades {grades} ({total} total). These must be:
- WORD PROBLEMS with real-life Canadian contexts (hockey, maple syrup, loonies/toonies, Tim Hortons, camping, school)
- Story-based and engaging for kids
- Include both English question and French translation
- Each question must have 4 multiple-choice answers
- Include a hint (don't give away answer) and 2 solution steps

Output as valid JSON (no markdown fences, no extra text). Format:
[
  {{
    "grade": 3,
    "topic": "Addition & Subtraction",
    "question": "English question text",
    "questionFr": "French translation",
    "choices": ["3", "5", "7", "8"],
    "answer": "5",
    "hint": "Think about adding the groups together",
    "steps": ["First add 2 + 3", "You get 5"]
  }}
]

RULES:
- answer must exactly match one of the choices
- Each grade should cover different topics from the curriculum
- Use age-appropriate language
- Make stories fun and relatable for Canadian kids
"""


def validate_question(q):
    """Return list of problems with this question dict (empty = valid)."""
    problems = []
    if not isinstance(q.get("grade"), int) or not 1 <= q["grade"] <= 12:
        problems.append("grade missing or out of range")
    for field in ("topic", "question", "questionFr", "hint"):
        if not isinstance(q.get(field), str) or not q[field].strip():
            problems.append(f"{field} missing/empty")
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) != 4 or len(set(map(str, choices))) != 4:
        problems.append("choices must be 4 unique values")
    elif str(q.get("answer")) not in [str(c) for c in choices]:
        problems.append("answer not among choices")
    steps = q.get("steps")
    if not isinstance(steps, list) or len(steps) != 2 or not all(str(s).strip() for s in steps):
        problems.append("steps must be a list of 2")
    return problems


def main():
    client = OpenAI(base_url=LOCAL_URL, api_key="local", timeout=600)
    total = len(GRADES) * QUESTIONS_PER_GRADE
    prompt = PROMPT.format(
        n=QUESTIONS_PER_GRADE,
        grades=", ".join(map(str, GRADES)),
        total=total,
    )
    print(f"INFO: Requesting {total} questions (grades {GRADES}) from {LOCAL_MODEL} ...")
    resp = client.chat.completions.create(
        model=LOCAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4096,
    )
    raw = resp.choices[0].message.content.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"FAIL: invalid JSON: {e}")
        print(raw[:800])
        sys.exit(1)

    if not isinstance(questions, list):
        print("FAIL: response is not a JSON array")
        sys.exit(1)

    valid = 0
    for i, q in enumerate(questions, 1):
        problems = validate_question(q)
        status = "OK " if not problems else "BAD"
        print(f"{status} G{q.get('grade')}: {q.get('question', '')[:90]}")
        if problems:
            print(f"     -> {'; '.join(problems)}")
            print(f"     raw: {json.dumps(q, ensure_ascii=False)[:300]}")
        else:
            print(f"     answer: {q['answer']} | choices: {q['choices']}")
            valid += 1

    print(f"\nResult: {valid}/{len(questions)} valid "
          f"({100.0 * valid / max(len(questions), 1):.0f}% acceptance)")
    sys.exit(0 if valid == len(questions) else 1)


if __name__ == "__main__":
    main()
