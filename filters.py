"""Evaluate explicit conditions, keeping missing evidence separate from failure."""

import math
import operator

OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "in": lambda actual, expected: actual in expected,
}
NUMERIC_FIELDS = {"employee_count", "revenue", "year_founded"}
NUMERIC_OPERATORS = set(OPERATORS) - {"in"}


def is_country_code(value):
    if not isinstance(value, str):
        return False
    code = value.strip()
    return len(code) == 2 and code.isascii() and code.isalpha()


def is_nonnegative_number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def is_founding_year(value):
    return 1 <= value <= 9999 and value == int(value)


def check_filters(company, conditions):
    checks = []
    for condition in conditions:
        field, op, expected = (
            condition["field"],
            condition["operator"],
            condition["value"],
        )
        if field == "country_code":
            allowed = {"==", "in"}
        elif field == "is_public":
            allowed = {"=="}
        elif field in NUMERIC_FIELDS:
            allowed = NUMERIC_OPERATORS
        else:
            raise ValueError(f"Unsupported filter field: {field}")
        if op not in allowed:
            raise ValueError(f"Unsupported operator for {field}: {op}")
        if field == "country_code":
            codes = expected if op == "in" else [expected]
            if (
                not isinstance(codes, list)
                or not codes
                or not all(map(is_country_code, codes))
            ):
                raise ValueError("Expected country code(s) with two letters")
            address = company.get("address")
            actual = address.get(field) if isinstance(address, dict) else None
            valid = is_country_code(actual)
            if valid:
                actual = actual.strip().casefold()
            expected = (
                [code.strip().casefold() for code in codes]
                if op == "in"
                else codes[0].strip().casefold()
            )
        elif field == "is_public":
            if type(expected) is not bool:
                raise ValueError("Expected a boolean for is_public")
            actual = company.get(field)
            valid = type(actual) is bool
        else:
            if not is_nonnegative_number(expected):
                raise ValueError(f"Expected a nonnegative finite threshold for {field}")
            if field == "year_founded" and not is_founding_year(expected):
                raise ValueError("Expected an integer founding year from 1 to 9999")
            actual = company.get(field)
            valid = is_nonnegative_number(actual)
            if valid and field == "year_founded":
                valid = is_founding_year(actual)

        if not valid:
            status = "unknown"
        elif OPERATORS[op](actual, expected):
            status = "pass"
        else:
            status = "fail"
        checks.append(
            {
                "field": field,
                "operator": op,
                "expected": expected,
                "actual": actual,
                "status": status,
            }
        )

    statuses = {check["status"] for check in checks}
    if "fail" in statuses:
        status = "fail"
    elif "unknown" in statuses:
        status = "unknown"
    else:
        status = "pass"
    return {"status": status, "checks": checks}
