"""Run the canonical Python question-quality conformance fixtures."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from question_quality import conformance_result, equivalent_strings, parse_value, validate_question


ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "spec" / "conformance-fixtures.json"


def assert_fixtures(fixtures: dict, result: dict) -> None:
    for case, actual in zip(fixtures["parse"], result["parse"]):
        expected = case["expect"]
        if expected == "PARSE_FAILED":
            if actual["result"].get("status") != "PARSE_FAILED" or actual["result"].get("code") != case.get("code"):
                raise AssertionError(f"parse fixture failed: {case['input']}: {actual}")
        elif actual["result"] != expected:
            raise AssertionError(f"parse fixture failed: {case['input']}: {actual['result']} != {expected}")
    for case, actual in zip(fixtures["equivalence"], result["equivalence"]):
        if actual["equal"] != case["equal"] or (not case["equal"] and actual["code"] != case.get("code")):
            raise AssertionError(f"equivalence fixture failed: {case}: {actual}")
    for case, actual in zip(fixtures["forbidden_fixes"], result["forbidden_fixes"]):
        if actual["verdict"] != "ERROR" or actual["code"] != case["code"]:
            raise AssertionError(f"forbidden fixer fixture failed: {case}: {actual}")
    for case, actual in zip(fixtures["questions"], result["questions"]):
        expected = case["expect"]
        if actual["verdict"] != expected["verdict"] or actual["codes"] != expected["codes"]:
            raise AssertionError(f"question fixture failed: {case['id']}: {actual}")
    for case, actual in zip(fixtures["bounded_termination"], result["bounded_termination"]):
        if actual["code"] != case["expect"]["code"] or not actual["must_terminate"]:
            raise AssertionError(f"termination fixture failed: {case['id']}: {actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(ROOT / "data" / "conformance" / "python.json"))
    args = parser.parse_args()
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    result = conformance_result(fixtures)
    assert_fixtures(fixtures, result)
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(output + "\n")
    print(f"Python conformance passed: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, json.JSONDecodeError) as exc:
        print(f"Conformance failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
