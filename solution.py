"""Entry point for the Intent Qualification challenge solution."""

import argparse
import json
import sys

from data_loader import load_companies
from keyword_search import search_companies, tokenize
from filtered_search import search_with_filters


def main():
    # Preserve company names with diacritics when output is redirected on Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Search company profiles by keyword.")
    parser.add_argument("--query", help="Words to search for in company profiles")
    parser.add_argument("--top", type=int, default=10, help="Maximum results (default: 10)")
    parser.add_argument("--method", choices=("keyword", "filters"), default="keyword")
    args = parser.parse_args()
    if args.top < 1:
        parser.error("--top must be a positive integer")
    if args.query is not None and not tokenize(args.query):
        parser.error("--query must contain at least one word or number")

    companies = load_companies()
    print(f"Loaded company records: {len(companies)}")
    if args.query is None:
        return

    if args.method == "filters":
        output = search_with_filters(companies, args.query, args.top)
        print("Parsed query:")
        print(json.dumps(output["parsed_query"], indent=2, ensure_ascii=False))
        print(f"Structured filter counts: {output['counts']}")
        print("Candidates passing extracted filters (full intent is not yet qualified):")
        show_results(output["results"])
        print("\nCandidates with unknown filter conditions (separate from passing candidates):")
        show_results(output["uncertain_results"])
        return

    results = search_companies(companies, args.query, args.top)
    show_results(results)


def show_results(results):
    if not results:
        print("No keyword matches found.")
        return

    print("\nKeyword results (score = number of distinct query words found):")
    for rank, result in enumerate(results, start=1):
        name = result["company"].get("operational_name") or "Unnamed company"
        words = ", ".join(result["matched_words"])
        print(f"{rank}. {name} | Score: {result['score']} | Matched words: {words}")


if __name__ == "__main__":
    main()
