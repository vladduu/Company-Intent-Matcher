"""Print a basic overview of the company dataset without changing it."""

import json
from collections import Counter
from pathlib import Path


def main():
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "companies.jsonl"

    companies = []
    with dataset_path.open(encoding="utf-8") as dataset:
        for line in dataset:
            if line.strip():
                companies.append(json.loads(line))

    print(f"Company records: {len(companies)}")

    fields = sorted({field for company in companies for field in company})
    print("\nMissing values per field (absent or null):")
    for field in fields:
        missing = sum(company.get(field) is None for company in companies)
        print(f"  {field}: {missing}")

    # Count extra copies, rather than all rows in a duplicate group.
    records = Counter(json.dumps(company, sort_keys=True) for company in companies)
    duplicates = sum(count - 1 for count in records.values())
    print(f"\nExact duplicate extra records: {duplicates}")

    print("\nFields with mixed non-null types:")
    for field in fields:
        types = Counter(
            type(company[field]).__name__
            for company in companies
            if company.get(field) is not None
        )
        if len(types) > 1:
            counts = ", ".join(f"{name}: {count}" for name, count in sorted(types.items()))
            print(f"  {field}: {counts}")


if __name__ == "__main__":
    main()
