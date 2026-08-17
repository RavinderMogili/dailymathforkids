"""Build and query the deterministic historical quiz quarantine manifest."""

from __future__ import annotations

import collections
import json
import pathlib
import re
import sys
from typing import Any, Iterable

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate_quiz

ROOT = SCRIPT_DIR.parent
DAILY_DIR = ROOT / "daily"
DEFAULT_MANIFEST = ROOT / "data" / "quarantine" / "historical.json"
GRADE_ORDER = {f"G{i}": i for i in range(1, 13)}
HIDDEN_CODES = {
    "NO_CORRECT_OPTION",
    "MULTIPLE_CORRECT_OPTIONS",
    "SOLVER_DISAGREEMENT",
    "UNIT_ASSERTION",
    "DUPLICATE_CHOICES",
    "CHOICE_COUNT",
    "CHOICE_IS_PREFIX_OF_CHOICE",
    "MISSING_FIELD",
    "PLACEHOLDER_TEXT",
    "ZERO_DENOMINATOR",
    "REMAINDER_GE_DIVISOR",
    "MALFORMED_SIGN",
}
FLAGGED_CODES = {
    "DUPLICATE_RECENT_QUESTION",
    "FRACTION_NOT_LOWEST_TERMS",
    "FRACTION_DENOMINATOR_ONE",
    "IMPROPER_FRACTION_FOR_GRADE",
    "DUPLICATE_QUESTION_NUMBER",
}


def _item_key(record: dict[str, Any]) -> tuple[str, int, int]:
    return (
        str(record["date"]),
        GRADE_ORDER.get(str(record["grade"]), 99),
        int(record["question_index"]),
    )


def build_manifest(daily_dir: pathlib.Path = DAILY_DIR) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for path in sorted(daily_dir.glob("*.md")):
        date = path.stem
        result = validate_quiz.validate_run(path, date)
        questions = {
            (str(question["grade"]), int(question["question_index"])): question
            for question in result["questions"]
        }
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = collections.defaultdict(list)
        for issue in result["issues"]:
            if (
                issue["level"] == "error"
                and issue["grade"] in GRADE_ORDER
                and int(issue["question_index"]) > 0
            ):
                grouped[(str(issue["grade"]), int(issue["question_index"]))].append(issue)
        for (grade, question_index), issues in sorted(
            grouped.items(),
            key=lambda item: (GRADE_ORDER[item[0][0]], item[0][1]),
        ):
            question = questions.get((grade, question_index), {})
            codes = sorted({
                str(issue["code"])
                for issue in issues
                if str(issue["code"]) in HIDDEN_CODES | FLAGGED_CODES
            })
            if not codes:
                continue
            messages = sorted({
                str(issue["message"])
                for issue in issues
                if issue.get("message") and str(issue["code"]) in codes
            })
            verdict = str(question.get("verdict") or "ERROR")
            if verdict == "VALID":
                verdict = "ERROR"
            disposition = "hidden" if any(code in HIDDEN_CODES for code in codes) else "flagged"
            records.append({
                "date": date,
                "grade": grade,
                "question_index": question_index,
                "authored_number": question.get("authored_number"),
                "codes": codes,
                "reason": "; ".join(messages) or "; ".join(codes),
                "verification_result": verdict,
                "disposition": disposition,
                "restoration_status": "quarantined" if disposition == "hidden" else "visible",
                "restoration_verification": None,
            })

    records.sort(key=_item_key)
    by_code: dict[str, dict[str, int]] = {}
    by_grade: dict[str, dict[str, int]] = {}
    for record in records:
        disposition = record["disposition"]
        grade = record["grade"]
        for code in record["codes"]:
            by_code.setdefault(code, {"hidden": 0, "flagged": 0})[disposition] += 1
        by_grade.setdefault(grade, {"hidden": 0, "flagged": 0})[disposition] += 1
    return {
        "version": 1,
        "items": records,
        "summary": {
            "hidden_items": sum(1 for record in records if record["disposition"] == "hidden"),
            "flagged_items": sum(1 for record in records if record["disposition"] == "flagged"),
            "by_code": dict(sorted(by_code.items())),
            "by_grade": {
                grade: by_grade[grade]
                for grade in sorted(by_grade, key=lambda value: GRADE_ORDER.get(value, 99))
            },
        },
    }


def write_manifest(
    output: pathlib.Path = DEFAULT_MANIFEST,
    daily_dir: pathlib.Path = DAILY_DIR,
) -> dict[str, Any]:
    manifest = build_manifest(daily_dir)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def load_manifest(path: pathlib.Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": 1,
            "items": [],
            "summary": {"hidden_items": 0, "flagged_items": 0, "by_code": {}, "by_grade": {}},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("invalid quarantine manifest")
    for item in data["items"]:
        required = (
            "date",
            "grade",
            "question_index",
            "codes",
            "reason",
            "verification_result",
            "disposition",
            "restoration_status",
            "restoration_verification",
        )
        if not isinstance(item, dict) or any(key not in item for key in required):
            raise ValueError("quarantine records must name every required field")
        if item["disposition"] not in {"hidden", "flagged"}:
            raise ValueError("invalid quarantine disposition")
        if item["restoration_status"] not in {"quarantined", "visible", "restored"}:
            raise ValueError("invalid restoration status")
        if item["disposition"] == "hidden" and item["restoration_status"] not in {"quarantined", "restored"}:
            raise ValueError("hidden records must be quarantined or restored")
        if item["disposition"] == "flagged" and item["restoration_status"] != "visible":
            raise ValueError("flagged records must remain visible")
        if item["restoration_status"] == "restored" and not str(item["restoration_verification"]).strip():
            raise ValueError("restored records require independent verification")
    return data


def is_quarantined(
    date: str,
    grade: str,
    question_index: int,
    manifest: dict[str, Any] | None = None,
) -> bool:
    manifest = manifest or load_manifest()
    return any(
        str(item.get("date")) == date
        and str(item.get("grade")) == grade
        and item.get("question_index") == question_index
        and item.get("disposition") == "hidden"
        and item.get("restoration_status") == "quarantined"
        for item in manifest.get("items", [])
    )


def date_has_quarantine(
    date: str,
    manifest: dict[str, Any] | None = None,
) -> bool:
    manifest = manifest or load_manifest()
    return any(
        str(item.get("date")) == date
        and item.get("disposition") == "hidden"
        and item.get("restoration_status") == "quarantined"
        for item in manifest.get("items", [])
    )


def filter_archive_dates(
    dates: Iterable[str],
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    return list(dates)


def render_archive_html(
    manifest: dict[str, Any],
    daily_dir: pathlib.Path = DAILY_DIR,
) -> int:
    from gen_site import generate_html_from_text, markdown2

    def hide_existing_html(html: str, date: str) -> str:
        section_pattern = re.compile(
            r'(<div class="grade-section" data-grade="(G\d+)"[^>]*>.*?'
            r'<ol class="problems-list">)(.*?)(</ol>)',
            re.DOTALL,
        )
        tag_pattern = re.compile(r"</?li\b[^>]*>", re.I)

        def replace_section(match: re.Match[str]) -> str:
            prefix, grade, body, suffix = match.groups()
            depth = 0
            starts: list[tuple[int, int]] = []
            spans: list[tuple[int, int]] = []
            for tag in tag_pattern.finditer(body):
                if tag.group(0).startswith("</"):
                    depth -= 1
                    if depth == 0 and starts:
                        start, ordinal = starts.pop()
                        spans.append((start, tag.end(), ordinal))
                else:
                    if depth == 0:
                        starts.append((tag.start(), len(spans) + len(starts) + 1))
                    depth += 1
            replacements = []
            for start, end, ordinal in spans:
                if is_quarantined(date, grade, ordinal, manifest):
                    replacements.append((
                        start,
                        end,
                        f'<li class="quarantined-question" data-quarantined="true" '
                        f'data-question-index="{ordinal}" aria-hidden="true" style="display:none"></li>',
                    ))
            for start, end, value in sorted(replacements, reverse=True):
                body = body[:start] + value + body[end:]
            return prefix + body + suffix

        return section_pattern.sub(replace_section, html)

    rendered = 0
    for markdown_path in sorted(daily_dir.glob("*.md")):
        html_path = markdown_path.with_suffix(".html")
        if not html_path.exists():
            continue
        if markdown2 is None:
            html = html_path.read_text(encoding="utf-8")
            html_path.write_text(hide_existing_html(html, markdown_path.stem), encoding="utf-8")
        else:
            html_path.write_text(
                generate_html_from_text(
                    markdown_path.read_text(encoding="utf-8"),
                    markdown_path.stem,
                    quarantine_manifest=manifest,
                ),
                encoding="utf-8",
            )
        rendered += 1
    return rendered


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build the historical quiz quarantine manifest.")
    parser.add_argument("--daily-dir", type=pathlib.Path, default=DAILY_DIR)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--render-html",
        action="store_true",
        help="Render existing archive HTML with hidden items as ordinal-preserving placeholders.",
    )
    args = parser.parse_args(argv)
    manifest = write_manifest(args.output, args.daily_dir)
    if args.render_html:
        print(f"Rendered archive pages: {render_archive_html(manifest, args.daily_dir)}")
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
