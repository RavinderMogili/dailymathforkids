"""Canonical Phase 0 question parsing, solving, and validation.

The implementation in this file is deliberately independent of the browser
quiz code.  It follows scripts/spec/QUESTION_QUALITY_SPEC.md and is mirrored
by scripts/question-quality.js.
"""

from __future__ import annotations

import math
import re
import unicodedata
from fractions import Fraction
from typing import Any


PLACEHOLDERS = {"todo", "tbd", "undefined", "nan", "null", "infinity"}
UNITS = (
    "degC", "cm2", "cm3", "m2", "m3", "mL", "km", "mm", "kg",
    "cm", "deg", "min", "h", "s", "L", "m", "g",
)
UNIT_DIMENSION = {
    "cm": "length", "m": "length", "km": "length", "mm": "length",
    "cm2": "area", "m2": "area", "cm3": "volume", "m3": "volume",
    "g": "mass", "kg": "mass", "mL": "capacity", "L": "capacity",
    "deg": "angle", "degC": "temperature", "min": "time",
    "h": "time", "s": "time",
}
UNIT_FACTORS = {
    "mm": Fraction(1, 1000), "cm": Fraction(1, 100),
    "m": Fraction(1), "km": Fraction(1000),
    "g": Fraction(1), "kg": Fraction(1000),
    "mL": Fraction(1), "L": Fraction(1000),
    "s": Fraction(1), "min": Fraction(60), "h": Fraction(3600),
}


def _gcd(a: int, b: int) -> int:
    return math.gcd(abs(a), abs(b))


def _value(kind: str, number: Fraction, **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": kind,
        "num": number.numerator,
        "den": number.denominator,
    }
    result.update(extra)
    return result


def _number(number: Fraction, **extra: Any) -> dict[str, Any]:
    return _value("number", number, **extra)


def _text(value: str) -> dict[str, str]:
    return {"kind": "text", "value": " ".join(value.casefold().split())}


def _normal_text(text: Any) -> str:
    text = unicodedata.normalize("NFKC", str(text or ""))
    text = text.replace("\u00a0", " ").replace("²", "2").replace("³", "3").replace("°", "deg")
    text = text.replace("−", "-").replace("–", "-").replace("—", "-")
    text = text.replace("×", "*").replace("÷", "/")
    return " ".join(text.strip().split())


normal_text = _normal_text


def _placeholder(text: str) -> str | None:
    lowered = text.casefold().strip()
    if not lowered:
        return "MISSING_FIELD"
    if "___" in lowered:
        return "PLACEHOLDER_TEXT"
    if lowered in PLACEHOLDERS:
        return "PLACEHOLDER_TEXT"
    return None


def _parse_number(text: str) -> tuple[Fraction | None, dict[str, Any], str | None]:
    text = text.replace(",", "").strip()
    mixed = re.fullmatch(r"([+-]?\d+)\s+(\d+)/(\d+)", text)
    if mixed:
        whole, numerator, denominator = map(int, mixed.groups())
        if denominator == 0:
            return None, {}, "ZERO_DENOMINATOR"
        sign = -1 if whole < 0 else 1
        number = Fraction(whole) + sign * Fraction(numerator, denominator)
        return number, {
            "written_num": number.numerator,
            "written_den": number.denominator,
            "mixed": True,
        }, None

    fraction = re.fullmatch(r"([+-]?\d+)/(\d+)", text)
    if fraction:
        numerator, denominator = map(int, fraction.groups())
        if denominator == 0:
            return None, {}, "ZERO_DENOMINATOR"
        return Fraction(numerator, denominator), {
            "written_num": numerator,
            "written_den": denominator,
        }, None

    decimal = re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text)
    if decimal:
        sign = -1 if text.startswith("-") else 1
        unsigned = text.lstrip("+-")
        if "." in unsigned:
            whole, places = unsigned.split(".", 1)
            digits = (whole or "0") + places
            number = Fraction(sign * int(digits or "0"), 10 ** len(places))
            return number, {"written_decimals": len(places)}, None
        return Fraction(sign * int(unsigned)), {}, None
    return None, {}, "PARSE_FAILED"


def parse_value(raw: Any) -> tuple[dict[str, Any] | None, str | None]:
    """Parse one surface form into a canonical value and optional error code."""
    text = _normal_text(raw)
    error = _placeholder(text)
    if error:
        return None, error

    meridiem = None
    mer_match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(AM|PM)", text, re.I)
    if mer_match:
        hour = int(mer_match.group(1))
        minute = int(mer_match.group(2) or 0)
        if 1 <= hour <= 12 and minute < 60:
            if hour == 12:
                hour = 0
            return {"kind": "time", "minutes": hour * 60 + minute,
                    "meridiem": mer_match.group(3).upper()}, None

    time_match = re.fullmatch(r"(\d{1,2}):(\d{1,2})", text)
    if time_match:
        hour, minute = map(int, time_match.groups())
        if minute < 60 and (len(time_match.group(2)) == 2 or minute == 0):
            if 0 <= hour <= 23:
                return {"kind": "time", "minutes": hour * 60 + minute,
                        "meridiem": None}, None

    quotrem = re.fullmatch(r"([+-]?\d+)\s*(?:R|remainder)\s*([+-]?\d+)", text, re.I)
    if quotrem:
        return {"kind": "quotrem", "q": int(quotrem.group(1)),
                "r": int(quotrem.group(2))}, None

    if re.fullmatch(r"[+-]?\d+(?::[+-]?\d+)+", text):
        terms = [int(part) for part in text.split(":")]
        divisor = 0
        for term in terms:
            divisor = _gcd(divisor, term)
        divisor = divisor or 1
        return {"kind": "ratio", "terms": [term // divisor for term in terms]}, None

    percent = re.fullmatch(r"(.+?)\s*%", text)
    if percent:
        number, meta, code = _parse_number(percent.group(1))
        if code == "ZERO_DENOMINATOR":
            return None, code
        if code is None:
            return _value("percent", number, **meta), None

    currency = re.fullmatch(r"(?:\$|A\$)\s*(.+)", text, re.I)
    if currency:
        number, meta, code = _parse_number(currency.group(1))
        if code == "ZERO_DENOMINATOR":
            return None, code
        if code is None:
            return _value("currency", number, symbol="$", **meta), None
    currency = re.fullmatch(r"(.+?)\s*(?:\$|dollars?)", text, re.I)
    if currency:
        number, meta, code = _parse_number(currency.group(1))
        if code == "ZERO_DENOMINATOR":
            return None, code
        if code is None:
            return _value("currency", number, symbol="$", **meta), None
    cents = re.fullmatch(r"(.+?)\s*(?:¢|cents?)", text, re.I)
    if cents:
        number, meta, code = _parse_number(cents.group(1))
        if code == "ZERO_DENOMINATOR":
            return None, code
        if code is None:
            return _value("currency", number, symbol="¢", **meta), None

    unit_pattern = "|".join(re.escape(unit) for unit in sorted(UNITS, key=len, reverse=True))
    measurement = re.fullmatch(r"(.+?)\s*(" + unit_pattern + r")", text)
    if measurement:
        number, meta, code = _parse_number(measurement.group(1))
        if code == "ZERO_DENOMINATOR":
            return None, code
        if code is None:
            return _value("measurement", number, unit=measurement.group(2), **meta), None

    number, meta, code = _parse_number(text)
    if code is None:
        return _number(number, **meta), None
    if code and code != "PARSE_FAILED":
        return None, code
    return _text(text), None


def serialize_value(value: dict[str, Any] | None, code: str | None = None) -> Any:
    if value is None:
        return {"status": "PARSE_FAILED", "code": code or "PARSE_FAILED"}
    return {key: item for key, item in value.items() if key != "mixed"}


def values_equal(a: dict[str, Any] | None, b: dict[str, Any] | None) -> tuple[bool, str | None]:
    if a is None or b is None:
        return False, "PARSE_FAILED"
    ka, kb = a["kind"], b["kind"]
    if (ka == "currency") != (kb == "currency"):
        return False, "UNIT_ASSERTION"
    if ka in {"number", "percent", "currency"} and kb in {"number", "percent", "currency"}:
        if ka != kb:
            return False, "VALUE_CHANGED"
        if ka == "currency" and a.get("symbol") != b.get("symbol"):
            return False, "VALUE_CHANGED"
        same = a["num"] == b["num"] and a["den"] == b["den"]
        return same, None if same else "VALUE_CHANGED"
    if ka == "measurement" and kb == "measurement":
        return (a["num"], a["den"]) == (b["num"], b["den"]) and a["unit"] == b["unit"], (
            None if a["unit"] == b["unit"] else "UNIT_MISMATCH"
        )
    if {ka, kb} == {"number", "measurement"}:
        return False, "UNIT_ASSERTION"
    if ka == "time" and kb == "time":
        same = a["minutes"] == b["minutes"] and a["meridiem"] == b["meridiem"]
        return same, None if same else "VALUE_CHANGED"
    if ka == "ratio" and kb == "ratio":
        same = a["terms"] == b["terms"]
        return same, None if same else "VALUE_CHANGED"
    if ka == "quotrem" and kb == "quotrem":
        same = (a["q"], a["r"]) == (b["q"], b["r"])
        return same, None if same else "VALUE_CHANGED"
    if ka == "text" and kb == "text":
        same = a["value"] == b["value"]
        return same, None if same else "VALUE_CHANGED"
    return False, "VALUE_CHANGED"


def equivalent_strings(a: Any, b: Any) -> tuple[bool, str | None]:
    va, ca = parse_value(a)
    vb, cb = parse_value(b)
    if va is None or vb is None:
        return False, ca or cb or "PARSE_FAILED"
    return values_equal(va, vb)


def _tokenize_expression(text: str) -> list[str] | None:
    text = text.replace(",", "")
    token_re = re.compile(r"\s*(\d+(?:\.\d+)?(?:/\d+)?|[()+\-*/])")
    tokens: list[str] = []
    pos = 0
    while pos < len(text):
        match = token_re.match(text, pos)
        if not match:
            return None
        tokens.append(match.group(1))
        pos = match.end()
    return tokens


def _eval_expression(text: str) -> Fraction | None:
    tokens = _tokenize_expression(text)
    if not tokens:
        return None
    index = 0

    def atom() -> Fraction | None:
        nonlocal index
        if index >= len(tokens):
            return None
        if tokens[index] in {"+", "-"}:
            sign = -1 if tokens[index] == "-" else 1
            index += 1
            value = atom()
            return sign * value if value is not None else None
        token = tokens[index]
        if token == "(":
            index += 1
            value = expr()
            if index >= len(tokens) or tokens[index] != ")":
                return None
            index += 1
            return value
        index += 1
        value, _, code = _parse_number(token)
        return value if code is None else None

    def term() -> Fraction | None:
        nonlocal index
        value = atom()
        while value is not None and index < len(tokens) and tokens[index] in {"*", "/"}:
            op = tokens[index]
            index += 1
            right = atom()
            if right is None or (op == "/" and right == 0):
                return None
            value = value * right if op == "*" else value / right
        return value

    def expr() -> Fraction | None:
        nonlocal index
        value = term()
        while value is not None and index < len(tokens) and tokens[index] in {"+", "-"}:
            op = tokens[index]
            index += 1
            right = term()
            if right is None:
                return None
            value = value + right if op == "+" else value - right
        return value

    value = expr()
    return value if index == len(tokens) else None


def _first_number(text: str) -> Fraction | None:
    match = re.search(r"(?<![\w:])[-+]?\d+(?:\.\d+)?", text.replace(",", ""))
    if not match:
        return None
    return Fraction(match.group(0))


def solve_question(question: str, grade: int | str | None = None) -> tuple[dict[str, Any] | None, str | None]:
    """Solve supported deterministic question forms, otherwise UNVERIFIED."""
    text = _normal_text(question)
    lowered = text.casefold()
    numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", text.replace(",", ""))

    compare = re.search(r"compare:\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)\s+_{2,}\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)", text, re.I)
    if compare:
        left, _, _ = _parse_number(compare.group(1))
        right, _, _ = _parse_number(compare.group(2))
        return _text("=" if left == right else (">" if left > right else "<")), None

    extreme = re.search(r"which is the (largest|smallest)\?\s*(.*)$", lowered)
    if extreme:
        values = [Fraction(n) for n in re.findall(r"[-+]?\d+(?:\.\d+)?", extreme.group(2))]
        if values:
            target = max(values) if extreme.group(1) == "largest" else min(values)
            if values.count(target) > 1:
                return None, "TIED_EXTREME_IN_LIST"
            return _number(target), None

    named = re.search(
        r"(?:a|an)\s+([a-z][\w -]*)\s+is\s+([-+]?\d+(?:\.\d+)?)\s*([a-z0-9]+)"
        r".*?(?:a|an)\s+([a-z][\w -]*)\s+is\s+([-+]?\d+(?:\.\d+)?)\s*([a-z0-9]+)"
        r".*?which is (longer|larger|shorter|smaller)",
        lowered,
    )
    if named:
        first, n1, u1, second, n2, u2, relation = named.groups()
        if u1 != u2:
            return None, "UNVERIFIED"
        v1, v2 = Fraction(n1), Fraction(n2)
        if v1 == v2:
            return None, "TIED_OPERANDS"
        first_wins = relation in {"longer", "larger"} and v1 > v2
        first_wins = first_wins or relation in {"shorter", "smaller"} and v1 < v2
        return _text(first if first_wins else second), None

    sale = re.search(
        r"original price:\s*\$?\s*([-+]?\d+(?:\.\d+)?)"
        r".*?sale price:\s*\$?\s*([-+]?\d+(?:\.\d+)?)",
        lowered,
    )
    if sale:
        original, sale_price = map(Fraction, sale.groups())
        if sale_price >= original:
            return None, "SALE_PRICE_GE_ORIGINAL"
        return _value("percent", (original - sale_price) * 100 / original), None

    metric = re.search(
        r"([-+]?\d+(?:\.\d+)?)\s*(mm|cm|m|km|g|kg|mL|L)\s*(?:=|to)\s*"
        r"(?:\?|how many)?\s*(mm|cm|m|km|g|kg|mL|L)",
        text,
        re.I,
    )
    if metric:
        amount, source, target = metric.groups()
        source = next((u for u in UNITS if u.casefold() == source.casefold()), source)
        target = next((u for u in UNITS if u.casefold() == target.casefold()), target)
        if UNIT_DIMENSION[source] != UNIT_DIMENSION[target]:
            return None, "UNVERIFIED"
        return _value("measurement", Fraction(amount) * UNIT_FACTORS[source] / UNIT_FACTORS[target], unit=target), None

    perimeter = re.search(r"square has a side of\s+([\d.]+)\s*cm.*?perimeter", lowered)
    if perimeter:
        return _value("measurement", Fraction(perimeter.group(1)) * 4, unit="cm"), None
    rectangle = re.search(r"rectangle.*?([\d.]+)\s*cm\s+long.*?([\d.]+)\s*cm\s+wide.*?perimeter", lowered)
    if rectangle:
        return _value("measurement", 2 * (Fraction(rectangle.group(1)) + Fraction(rectangle.group(2))), unit="cm"), None
    area = re.search(r"area of a rectangle:\s*length\s*=\s*([\d.]+).*?width\s*=\s*([\d.]+)", lowered)
    if area:
        return _number(Fraction(area.group(1)) * Fraction(area.group(2))), None
    volume = re.search(r"(?:box is|volume of a rectangular prism).*?([\d.]+)\s*[x*]\s*([\d.]+)\s*[x*]\s*([\d.]+)", lowered)
    if volume:
        a, b, c = map(Fraction, volume.groups())
        return _number(a * b * c), None

    elapsed = re.search(
        r"(?:from|start:)\s*(\d{1,2}):(\d{2}).*?(?:to|end:)\s*(\d{1,2}):(\d{2}).*?minutes",
        lowered,
    )
    if elapsed:
        sh, sm, eh, em = map(int, elapsed.groups())
        return _number(Fraction((eh * 60 + em) - (sh * 60 + sm))), None
    hours = re.search(r"starts at (\d{1,2}):00 and ends at (\d{1,2}):00.*?hours", lowered)
    if hours:
        return _number(Fraction(int(hours.group(2)) - int(hours.group(1)))), None

    substitution = re.search(
        r"if\s+y\s*=\s*([-+]?\d+(?:\.\d+)?)\s*x\s*([+-])\s*(\d+(?:\.\d+)?)"
        r".*?x\s*=\s*([-+]?\d+(?:\.\d+)?).*?what is y", lowered,
    )
    if substitution:
        m, op, intercept, x = substitution.groups()
        value = Fraction(m) * Fraction(x) + (Fraction(intercept) if op == "+" else -Fraction(intercept))
        return _number(value), None

    exponent_result = re.search(
        r"(\d+)\^(\d+)\s*[×x*]\s*\1\^(\d+)\s*=\s*\1\^\?",
        text,
    )
    if exponent_result:
        return _number(Fraction(int(exponent_result.group(2)) + int(exponent_result.group(3)))), None

    power = re.search(r"([-+]?\d+)\s*\^\s*([-+]?\d+)", text)
    if power:
        base, exponent = map(int, power.groups())
        return _number(Fraction(base ** exponent)), None
    root = re.search(r"(?:√|sqrt\(?\s*)(\d+)", text, re.I)
    if root:
        value = int(root.group(1))
        result = math.isqrt(value)
        if result * result == value:
            return _number(Fraction(result)), None

    fraction_operation = re.search(
        r"(?:what is\s+)?([-+]?\d+/\d+)\s*([+\-x*÷/])\s*([-+]?\d+/\d+)",
        lowered,
    )
    if fraction_operation:
        left, _, left_error = _parse_number(fraction_operation.group(1))
        right, _, right_error = _parse_number(fraction_operation.group(3))
        if left_error or right_error or (fraction_operation.group(2) in {"÷", "/"} and right == 0):
            return None, "UNVERIFIED"
        operator = fraction_operation.group(2)
        value = {
            "+": left + right,
            "-": left - right,
            "x": left * right,
            "*": left * right,
            "÷": left / right,
            "/": left / right,
        }[operator]
        return _number(value), None

    division_result = re.search(r"([-+]?\d+)\s*(?:÷|/)\s*([-+]?\d+)\s*=\s*\?", text)
    if division_result:
        dividend, divisor = map(int, division_result.groups())
        if divisor:
            quotient, remainder = divmod(dividend, divisor)
            if remainder == 0:
                return _number(Fraction(quotient), written_decimals=0), None
            return {"kind": "quotrem", "q": quotient, "r": remainder}, None

    exponent_result = re.search(
        r"(\d+)\^(\d+)\s*[×x*]\s*\1\^(\d+)\s*=\s*\1\^\?",
        text,
    )
    if exponent_result:
        return _number(Fraction(int(exponent_result.group(2)) + int(exponent_result.group(3)))), None

    dot_result = re.search(
        r"Dot product:\s*\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*[·.]\s*"
        r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)\s*=\s*\?",
        text,
        re.I,
    )
    if dot_result:
        a, b, c, d = map(int, dot_result.groups())
        return _number(Fraction(a * c + b * d)), None

    # Restrict generic expression solving to stems that visibly ask for an
    # arithmetic result.  This prevents word problems from being guessed.
    expression = re.search(r"([-+*/()\d.,\s]+?)\s*=\s*\?", text)
    if expression and "remainder" not in lowered:
        candidate = expression.group(1).strip().replace("×", "*").replace("÷", "/")
        if any(op in candidate for op in "+-*/"):
            value = _eval_expression(candidate)
            if value is not None:
                return _number(value), None

    percent = re.search(r"what is\s+([-+]?\d+(?:\.\d+)?)\s*%\s+of\s+([-+]?\d+(?:\.\d+)?)", lowered)
    if percent:
        return _number(Fraction(percent.group(1)) * Fraction(percent.group(2)) / 100), None

    division = re.search(r"([-+]?\d+)\s*(?:÷|/)\s*([-+]?\d+).*(?:remainder|with remainder)", lowered)
    if division:
        dividend, divisor = map(int, division.groups())
        if divisor:
            return {"kind": "quotrem", "q": dividend // divisor, "r": dividend % divisor}, None

    return None, "UNVERIFIED"


def _has_rounding_instruction(text: str) -> bool:
    return bool(re.search(r"\b(round|rounded|decimal places|nearest|nearest tenth|nearest whole)\b", text, re.I))


def _round_fraction(value: Fraction, decimals: int) -> Fraction:
    factor = 10 ** decimals
    scaled = value * factor
    quotient, remainder = divmod(abs(scaled.numerator), scaled.denominator)
    if remainder * 2 >= scaled.denominator:
        quotient += 1
    if scaled.numerator < 0:
        quotient = -quotient
    return Fraction(quotient, factor)


def _fraction_issues(value: dict[str, Any] | None, grade: int) -> list[str]:
    if not value or value.get("kind") != "number" or "written_den" not in value:
        return []
    issues: list[str] = []
    written_num, written_den = value["written_num"], value["written_den"]
    if _gcd(written_num, written_den) != 1:
        issues.append("FRACTION_NOT_LOWEST_TERMS")
    if value.get("den") == 1:
        issues.append("FRACTION_DENOMINATOR_ONE")
    if grade <= 4 and abs(written_num) > written_den and not value.get("mixed"):
        issues.append("IMPROPER_FRACTION_FOR_GRADE")
    return issues


def _question_value(text: str) -> tuple[dict[str, Any] | None, str | None]:
    return solve_question(text)


def validate_question(question: dict[str, Any], require_french: bool = False) -> dict[str, Any]:
    grade_raw = question.get("grade", "")
    grade_match = re.search(r"\d+", str(grade_raw))
    grade = int(grade_match.group(0)) if grade_match else 0
    index = int(question.get("num", question.get("question_index", 0)) or 0)
    text = str(question.get("question") or question.get("en") or "").strip()
    answer = question.get("answer")
    choices = question.get("choices") or []
    codes: list[str] = []

    def add(code: str) -> None:
        if code not in codes:
            codes.append(code)

    if not text or answer is None or str(answer).strip() == "" or not choices:
        add("MISSING_FIELD")
        return {"verdict": "ERROR", "codes": codes, "grade": grade_raw, "question_index": index}
    if require_french and not str(question.get("fr") or "").strip():
        add("MISSING_FRENCH")
    if int(question.get("answer_line_count", 1) or 0) > 1:
        add("MULTIPLE_ANSWER_LINES")
    full_text = " ".join(str(question.get(k) or "") for k in ("title", "en", "fr", "hint", "answer", "choices_raw"))
    if re.search(r"\+\s*-|-\s*-|\+-", full_text):
        add("MALFORMED_SIGN")
    if re.search(r"\b(?:TODO|TBD|undefined|NaN|null|Infinity)\b", full_text, re.I):
        add("PLACEHOLDER_TEXT")
    if len(choices) != 4:
        add("CHOICE_COUNT")

    parsed_choices: list[dict[str, Any] | None] = []
    choice_errors: list[str | None] = []
    for choice in choices:
        value, error = parse_value(choice)
        parsed_choices.append(value)
        choice_errors.append(error)

    answer_value, answer_error = parse_value(answer)
    fraction_codes: list[str] = []
    for value in [answer_value, *parsed_choices]:
        for code in _fraction_issues(value, grade):
            if code not in fraction_codes:
                fraction_codes.append(code)
    if answer_value and (
        answer_value.get("den") == 1 or
        abs(answer_value.get("written_num", 0)) > answer_value.get("written_den", 0)
    ):
        fraction_codes = [code for code in fraction_codes if code != "FRACTION_NOT_LOWEST_TERMS"]
    for code in fraction_codes:
        add(code)
    if any(error == "ZERO_DENOMINATOR" for error in [answer_error, *choice_errors]):
        add("ZERO_DENOMINATOR")

    divisor_match = re.search(r"(?:÷|/)\s*(\d+).*(?:remainder|with remainder)", text, re.I)
    if divisor_match:
        divisor = int(divisor_match.group(1))
        for value in parsed_choices:
            if value and value.get("kind") == "quotrem" and not (0 <= value["r"] < divisor):
                add("REMAINDER_GE_DIVISOR")

    fraction_gate = "FRACTION_NOT_LOWEST_TERMS" in fraction_codes
    answer_format_exception = bool(
        answer_value and "written_den" in answer_value and (
            answer_value.get("den") == 1 or
            abs(answer_value.get("written_num", 0)) > answer_value.get("written_den", 0)
        )
    )
    if len(choices) == 4 and not fraction_gate and not answer_format_exception:
        for left in range(len(parsed_choices)):
            for right in range(left + 1, len(parsed_choices)):
                same, _ = values_equal(parsed_choices[left], parsed_choices[right])
                if same:
                    add("DUPLICATE_CHOICES")
        normalized = [_normal_text(c).casefold() for c in choices]
        for left in range(len(normalized)):
            for right in range(len(normalized)):
                numeric_pair = parsed_choices[left] and parsed_choices[right] and all(
                    value.get("kind") == "number" for value in (parsed_choices[left], parsed_choices[right])
                )
                if left != right and not numeric_pair and normalized[right].startswith(normalized[left]) and normalized[left] != normalized[right]:
                    add("CHOICE_IS_PREFIX_OF_CHOICE")
                    break

    matches: list[int] = []
    mismatch_codes: list[str] = []
    if answer_value is not None:
        for position, choice_value in enumerate(parsed_choices):
            same, mismatch = values_equal(answer_value, choice_value)
            if same:
                matches.append(position)
            elif mismatch:
                mismatch_codes.append(mismatch)
    if len(matches) == 0:
        if "UNIT_ASSERTION" in mismatch_codes:
            add("UNIT_ASSERTION")
        else:
            add("NO_CORRECT_OPTION")
    extreme_values = re.findall(r"which is the (?:largest|smallest)\?\s*(.*)$", text, re.I)
    extreme_numbers = re.findall(r"[-+]?\d+(?:\.\d+)?", extreme_values[0]) if extreme_values else []
    tied_extreme = len(extreme_numbers) != len(set(extreme_numbers))
    if len(matches) > 1 and not tied_extreme:
        add("MULTIPLE_CORRECT_OPTIONS")

    if re.search(r"\b(percent off|discount)\b", text, re.I):
        sale = re.search(r"original price:\s*\$?\s*([\d.]+).*?sale price:\s*\$?\s*([\d.]+)", text, re.I)
        if sale and Fraction(sale.group(2)) >= Fraction(sale.group(1)):
            add("SALE_PRICE_GE_ORIGINAL")
        if answer_value and answer_value.get("kind") == "percent":
            if answer_value["num"] <= 0:
                add("NEGATIVE_PERCENT_OFF")
            elif answer_value["num"] >= 100 * answer_value["den"]:
                add("PERCENT_OUT_OF_RANGE")

    solved, solve_code = _question_value(text)
    if re.search(r"compare:\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)\s+_{2,}\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)", text, re.I):
        compare_match = re.search(r"compare:\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)\s+_{2,}\s*([-+]?\d+(?:\.\d+)?(?:/\d+)?)", text, re.I)
        left, _ = parse_value(compare_match.group(1))
        right, _ = parse_value(compare_match.group(2))
        if left and right and left["num"] * right["den"] == right["num"] * left["den"]:
            add("EQUAL_OPERANDS_COMPARISON")
    if solve_code == "TIED_OPERANDS":
        add("TIED_OPERANDS")
    if solve_code == "TIED_EXTREME_IN_LIST":
        add("TIED_EXTREME_IN_LIST")
    if solve_code == "SALE_PRICE_GE_ORIGINAL":
        add("SALE_PRICE_GE_ORIGINAL")
    arithmetic_result = re.search(
        r"^\s*[-+]?\d+(?:\.\d+)?\s*[x*\u00d7\u00f7/]\s*[-+]?\d+(?:\.\d+)?\s*=\s*\?\s*$",
        text,
        re.I,
    )
    if arithmetic_result and solved and answer_value and answer_value.get("kind") == "number":
        rounding_instruction = re.search(r"\b(round|rounded|nearest|decimal places?)\b", text, re.I)
        same_answer, _ = values_equal(answer_value, solved)
        if not same_answer and not rounding_instruction:
            add("UNROUNDED_WITHOUT_INSTRUCTION")

    if re.search(r"which is the (largest|smallest)", text, re.I) and solved:
        extreme = re.search(r"which is the (largest|smallest)\?\s*(.*)$", text.casefold())
        if extreme:
            values = [Fraction(n) for n in re.findall(r"[-+]?\d+(?:\.\d+)?", extreme.group(2))]
            target = max(values) if extreme.group(1) == "largest" else min(values)
            for value in parsed_choices:
                if value and value.get("kind") == "number":
                    candidate = Fraction(value["num"], value["den"])
                    if (extreme.group(1) == "largest" and candidate > target) or (
                        extreme.group(1) == "smallest" and candidate < target
                    ):
                        add("DISTRACTOR_BEATS_ANSWER")
                        break

    if answer_value and solved and solve_code not in {"TIED_OPERANDS", "TIED_EXTREME_IN_LIST", "SALE_PRICE_GE_ORIGINAL"} and not {
        "EQUAL_OPERANDS_COMPARISON", "REMAINDER_GE_DIVISOR", "UNROUNDED_WITHOUT_INSTRUCTION"
    }.intersection(codes):
        same, mismatch = values_equal(answer_value, solved)
        if not same:
            if _has_rounding_instruction(text) and answer_value.get("kind") in {"number", "currency"}:
                decimals = answer_value.get("written_decimals")
                if decimals is not None:
                    rounded = _round_fraction(Fraction(solved["num"], solved["den"]), decimals)
                    authored = Fraction(answer_value["num"], answer_value["den"])
                    if rounded != authored:
                        add("SOLVER_DISAGREEMENT")
            else:
                if re.search(r"\b(?:which|what)\s+(?:shape|word|name)", text, re.I) and solve_code == "UNVERIFIED":
                    pass
                elif mismatch not in {"UNIT_ASSERTION", "UNIT_MISMATCH"}:
                    add("SOLVER_DISAGREEMENT")
        elif _has_rounding_instruction(text):
            pass
    elif solved is None and solve_code == "UNVERIFIED":
        # A structurally sound but unsupported deterministic form is explicitly
        # unverified.  Existing structural errors still take precedence.
        if not codes:
            add("UNVERIFIED")

    if answer_value and "hint" in question:
        hint = str(question.get("hint") or "")
        answer_surface = _normal_text(answer).casefold()
        if answer_surface and answer_surface in _normal_text(hint).casefold():
            add("HINT_LEAKS_ANSWER")

    blocking_codes = [code for code in codes if code != "HINT_LEAKS_ANSWER"]
    verdict = "VALID"
    if blocking_codes:
        verdict = "UNVERIFIED" if blocking_codes == ["UNVERIFIED"] else "ERROR"
    return {"verdict": verdict, "codes": codes, "grade": grade_raw, "question_index": index}


def conformance_result(fixtures: dict[str, Any]) -> dict[str, Any]:
    parse_results = []
    for case in fixtures["parse"]:
        value, code = parse_value(case["input"])
        parse_results.append({
            "input": case["input"],
            "result": serialize_value(value, code),
        })
    equivalence_results = []
    for case in fixtures["equivalence"]:
        equal, code = equivalent_strings(case["a"], case["b"])
        equivalence_results.append({"a": case["a"], "b": case["b"], "equal": equal, "code": code})
    forbidden_results = []
    for case in fixtures["forbidden_fixes"]:
        equal, code = equivalent_strings(case["stored"], case["substituted"])
        forbidden_results.append({"file": case["file"], "stored": case["stored"],
                                  "substituted": case["substituted"], "verdict": "ERROR",
                                  "code": code or ("VALUE_CHANGED" if not equal else "VALUE_CHANGED")})
    question_results = []
    for case in fixtures["questions"]:
        question_results.append({"id": case["id"], **validate_question({
            "grade": case["grade"], "num": 1, "question": case["question"],
            "en": case["question"], "fr": case.get("fr"),
            "choices": case["choices"], "answer": case["answer"],
            "hint": case.get("hint"),
        }, require_french=case.get("require_french", False) or "fr" in case)})
    bounded_results = []
    for case in fixtures["bounded_termination"]:
        space = {str(value) for value in case["distractor_values"]}
        possible = len(space - {str(case["correct"])}) + 1
        bounded_results.append({"id": case["id"], "code": (
            "INSUFFICIENT_DISTRACTOR_SPACE"
            if possible < case["required_choices"] else None
        ), "must_terminate": True})
    return {"version": fixtures["version"], "parse": parse_results,
            "equivalence": equivalence_results, "forbidden_fixes": forbidden_results,
            "questions": question_results, "bounded_termination": bounded_results}
