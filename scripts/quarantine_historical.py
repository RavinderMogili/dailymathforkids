"""Build and query the deterministic historical quiz quarantine manifest."""

from __future__ import annotations

import collections
import json
import pathlib
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
            codes = sorted({str(issue["code"]) for issue in issues})
            messages = sorted({str(issue["message"]) for issue in issues if issue.get("message")})
            verdict = str(question.get("verdict") or "ERROR")
            if verdict == "VALID":
                verdict = "ERROR"
            records.append({
                "date": date,
                "grade": grade,
                "question_index": question_index,
                "authored_number": question.get("authored_number"),
                "codes": codes,
                "reason": "; ".join(messages) or "; ".join(codes),
                "verification_result": verdict,
                "restoration_status": "quarantined",
                "restoration_verification": None,
            })

    records.sort(key=_item_key)
    by_code = collections.Counter(code for record in records for code in record["codes"])
    by_grade = collections.Counter(record["grade"] for record in records)
    return {
        "version": 1,
        "items": records,
        "summary": {
            "quarantined_items": len(records),
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
        return {"version": 1, "items": [], "summary": {"quarantined_items": 0, "by_code": {}, "by_grade": {}}}
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
            "restoration_status",
            "restoration_verification",
        )
        if not isinstance(item, dict) or any(key not in item for key in required):
            raise ValueError("quarantine records must name every required field")
        if item["restoration_status"] not in {"quarantined", "restored"}:
            raise ValueError("invalid restoration status")
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
        and item.get("restoration_status") == "quarantined"
        for item in manifest.get("items", [])
    )


def filter_archive_dates(
    dates: Iterable[str],
    manifest: dict[str, Any] | None = None,
) -> list[str]:
    manifest = manifest or load_manifest()
    return [date for date in dates if not date_has_quarantine(date, manifest)]


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Build the historical quiz quarantine manifest.")
    parser.add_argument("--daily-dir", type=pathlib.Path, default=DAILY_DIR)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    manifest = write_manifest(args.output, args.daily_dir)
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
