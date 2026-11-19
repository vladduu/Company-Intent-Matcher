"""Repeat the keyword baseline evaluation using explicitly labeled profiles."""

import hashlib
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from data_loader import DEFAULT_DATASET_PATH, load_companies
from keyword_search import search_companies
from filtered_search import search_with_filters


def company_id(company):
    text = json.dumps(company, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Evaluate one search method on development queries")
    parser.add_argument("--method", choices=("keyword", "filters", "semantic", "hybrid"), default="keyword")
    args = parser.parse_args()
    path = Path(__file__).resolve().parent / "evaluation" / "development_cases.json"
    evaluation = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(DEFAULT_DATASET_PATH.read_bytes()).hexdigest()
    if digest != evaluation["dataset_sha256"]:
        raise ValueError("Dataset changed; review the evaluation cases before comparing results.")

    companies = load_companies()
    engine = None
    if args.method in ("semantic", "hybrid"):
        from semantic_search import SemanticSearch
        try:
            engine = SemanticSearch(companies)
        except (RuntimeError, OSError, ValueError) as error:
            parser.exit(1, f"Semantic search error: {error}\n")
    labels = {}
    valid_labels = {"relevant", "not_relevant", "insufficient_information"}
    known_ids = {company_id(company) for company in companies}
    for case in evaluation["cases"]:
        key = (case["query_id"], case["company_id"])
        if key in labels or case["label"] not in valid_labels or case["company_id"] not in known_ids:
            raise ValueError(f"Invalid or duplicate evaluation case: {key}")
        labels[key] = case["label"]

    print("Development evaluation: assistant-proposed labels, pending human review.")
    print("Confirmed relevant / 10 is a lower bound when judgments are uncertain or missing.")
    for query in evaluation["queries"]:
        if args.method != "keyword":
            output = (engine.search(query["text"], top=10, hybrid=args.method == "hybrid")
                      if engine is not None else search_with_filters(companies, query["text"], top=10))
            results = output["results"]
            print(f"\nStructured filter counts: {output['counts']}; unknown candidates excluded from passing list")
        else:
            results = search_companies(companies, query["text"], top=10)
        counts = Counter(labels.get((query["id"], company_id(r["company"])), "unjudged") for r in results)
        print(f"\n{query['id']}: {query['text']}")
        print(f"Returned: {len(results)}; relevant: {counts['relevant']}; "
              f"not relevant: {counts['not_relevant']}; "
              f"insufficient information: {counts['insufficient_information']}; "
              f"unjudged: {counts['unjudged']}")
        print(f"Confirmed-relevant@10: {counts['relevant'] / 10:.2f}")
        for rank, result in enumerate(results, 1):
            company = result["company"]
            label = labels.get((query["id"], company_id(company)), "unjudged")
            print(f"  {rank}. {company.get('operational_name')} | {label}")


if __name__ == "__main__":
    main()
