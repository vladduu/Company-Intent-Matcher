"""Print a basic overview of the company dataset without changing it."""

import json
from collections import Counter, defaultdict
from pathlib import Path


def main():
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "companies.jsonl"

    companies = []
    with dataset_path.open(encoding="utf-8") as dataset:
        for line in dataset:
            if line.strip():
                companies.append(json.loads(line))

    print(f"Company records: {len(companies)}")

    field_types = defaultdict(Counter)
    unique_records = set()
    for company in companies:
        unique_records.add(json.dumps(company, sort_keys=True))
        for field, value in company.items():
            types = field_types[field]
            if value is not None:
                types[type(value).__name__] += 1

    fields = sorted(field_types)
    print("\nMissing values per field (absent or null):")
    for field in fields:
        missing = len(companies) - sum(field_types[field].values())
        print(f"  {field}: {missing}")

    duplicates = len(companies) - len(unique_records)
    print(f"\nExact duplicate extra records: {duplicates}")

    print("\nFields with mixed non-null types:")
    for field in fields:
        types = field_types[field]
        if len(types) > 1:
            counts = ", ".join(
                f"{name}: {count}" for name, count in sorted(types.items())
            )
            print(f"  {field}: {counts}")


if __name__ == "__main__":
    main()
