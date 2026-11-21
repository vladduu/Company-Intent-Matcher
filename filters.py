"""Evaluate explicit conditions, keeping missing evidence separate from failure."""

import math
import operator


OPERATORS = {">": operator.gt, ">=": operator.ge, "<": operator.lt,
             "<=": operator.le, "==": operator.eq, "in": lambda actual, expected: actual in expected}
NUMERIC_FIELDS = {"employee_count", "revenue", "year_founded"}


def check_filters(company, conditions):
    checks = []
    for condition in conditions:
        field, op, expected = condition["field"], condition["operator"], condition["value"]
        if field not in {"country_code", "is_public"} | NUMERIC_FIELDS:
            raise ValueError(f"Unsupported filter field: {field}")
        allowed = {"==", "in"} if field == "country_code" else {"=="} if field == "is_public" else set(OPERATORS) - {"in"}
        if op not in allowed:
            raise ValueError(f"Unsupported operator for {field}: {op}")
        if field == "country_code":
            codes = expected if op == "in" else [expected]
            if not isinstance(codes, list) or not codes or any(
                    not isinstance(code, str) or len(code.strip()) != 2 or not code.strip().isascii()
                    or not code.strip().isalpha() for code in codes):
                raise ValueError("Expected country code(s) with two letters")
            address = company.get("address")
            actual = address.get(field) if isinstance(address, dict) else None
            valid = isinstance(actual, str) and len(actual.strip()) == 2 and actual.strip().isascii() and actual.strip().isalpha()
            if valid:
                actual = actual.strip().casefold()
            expected = [code.strip().casefold() for code in codes] if op == "in" else codes[0].strip().casefold()
        elif field == "is_public":
            if type(expected) is not bool:
                raise ValueError("Expected a boolean for is_public")
            actual = company.get(field)
            valid = type(actual) is bool
        else:
            if type(expected) not in (int, float) or not math.isfinite(expected) or expected < 0:
                raise ValueError(f"Expected a nonnegative finite threshold for {field}")
            if field == "year_founded" and (expected != int(expected) or not 1 <= expected <= 9999):
                raise ValueError("Expected an integer founding year from 1 to 9999")
            actual = company.get(field)
            valid = type(actual) in (int, float) and math.isfinite(actual) and actual >= 0
            if valid and field == "year_founded":
                valid = actual == int(actual) and 1 <= actual <= 9999

        status = "unknown" if not valid else ("pass" if OPERATORS[op](actual, expected) else "fail")
        checks.append({"field": field, "operator": op, "expected": expected,
                       "actual": actual, "status": status})

    statuses = {check["status"] for check in checks}
    status = "fail" if "fail" in statuses else "unknown" if "unknown" in statuses else "pass"
    return {"status": status, "checks": checks}
