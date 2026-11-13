"""Load company profiles without changing the original dataset."""

import ast
import json
from pathlib import Path


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "data" / "companies.jsonl"


def normalize_company(company):
    """Convert dictionary-like fields to dictionaries, preserving missing values."""
    normalized = company.copy()

    for field in ("address", "primary_naics"):
        value = company.get(field)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                # Some profiles use Python dictionary syntax with single quotes.
                try:
                    value = ast.literal_eval(value)
                except (ValueError, SyntaxError) as error:
                    raise ValueError(f"Invalid dictionary in {field}") from error

        if value is not None and not isinstance(value, dict):
            raise ValueError(f"{field} must be a dictionary or null")

        normalized[field] = value

    return normalized


def load_companies(dataset_path=DEFAULT_DATASET_PATH):
    """Read every JSONL record and normalize its fields."""
    companies = []

    with Path(dataset_path).open(encoding="utf-8") as dataset:
        for line_number, line in enumerate(dataset, start=1):
            if not line.strip():
                continue

            try:
                company = json.loads(line)
                if not isinstance(company, dict):
                    raise ValueError("Each record must be a JSON object")

                companies.append(normalize_company(company))
            except ValueError as error:
                raise ValueError(f"Line {line_number}: {error}") from error

    return companies
