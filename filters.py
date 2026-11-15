"""Evaluate explicit conditions, keeping missing evidence separate from failure."""

import math
import operator


OPERATORS = {">": operator.gt, ">=": operator.ge, "<": operator.lt,
             "<=": operator.le, "==": operator.eq}


def check_filters(company, conditions):
    checks = []
    for condition in conditions:
        field, op, expected = condition["field"], condition["operator"], condition["value"]
        if field not in {"country_code", "is_public", "employee_count"}:
            raise ValueError(f"Unsupported filter field: {field}")
        if op not in OPERATORS or (field != "employee_count" and op != "=="):
            raise ValueError(f"Unsupported operator for {field}: {op}")
        if field == "country_code":
            if not isinstance(expected, str) or not expected.strip():
                raise ValueError("Expected a country code string")
            address = company.get("address")
            actual = address.get(field) if isinstance(address, dict) else None
            valid = isinstance(actual, str) and bool(actual.strip())
            if valid:
                actual = actual.strip().casefold()
            expected = expected.strip().casefold()
        elif field == "is_public":
            if type(expected) is not bool:
                raise ValueError("Expected a boolean for is_public")
            actual = company.get(field)
            valid = type(actual) is bool
        else:
            if type(expected) not in (int, float) or not math.isfinite(expected) or expected < 0:
                raise ValueError("Expected a nonnegative finite employee threshold")
            actual = company.get(field)
            valid = type(actual) in (int, float) and math.isfinite(actual) and actual >= 0

        status = "unknown" if not valid else ("pass" if OPERATORS[op](actual, expected) else "fail")
        checks.append({"field": field, "operator": op, "expected": expected,
                       "actual": actual, "status": status})

    statuses = {check["status"] for check in checks}
    status = "fail" if "fail" in statuses else "unknown" if "unknown" in statuses else "pass"
    return {"status": status, "checks": checks}
