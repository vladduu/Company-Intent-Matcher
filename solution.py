"""Command-line entry point for single-query and batch company qualification."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter

from data_loader import DEFAULT_DATASET_PATH, load_companies
from keyword_search import tokenize
from cli_options import add_options, check_options
from pipeline import SearchPipeline


def read_queries(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError(
            "Query file must be a nonempty JSON list of {id, text} objects"
        )
    seen = set()
    for item in payload:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"].strip()
        ):
            raise ValueError("Every query needs a nonempty string id")
        if (
            item["id"] in seen
            or not isinstance(item.get("text"), str)
            or not tokenize(item["text"])
        ):
            raise ValueError(
                "Query IDs must be unique and text must contain words/numbers"
            )
        seen.add(item["id"])
    return payload


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Rank and qualify company profiles")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--query", help="One company search request")
    inputs.add_argument(
        "--queries", type=Path, help="JSON file containing query objects with id/text"
    )
    parser.add_argument(
        "--output", type=Path, help="Save all results, evidence and timings as JSON"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Show filters, scores, evidence and candidates needing review",
    )
    parser.add_argument(
        "--data", type=Path, default=DEFAULT_DATASET_PATH, help="Company JSONL dataset"
    )
    parser.add_argument("--top", type=int, default=10)
    add_options(parser, default_method="rerank")
    args = parser.parse_args()
    check_options(parser, args, args.top)
    if args.query is not None and not tokenize(args.query):
        parser.error("--query must contain words or numbers")
    if args.output and not (args.query or args.queries):
        parser.error("--output requires --query or --queries")
    try:
        queries = []
        if args.queries:
            queries = read_queries(args.queries)
        elif args.query:
            queries = [{"id": "query", "text": args.query}]

        if args.output:
            input_paths = {args.data.resolve()}
            if args.queries:
                input_paths.add(args.queries.resolve())
            if args.output.resolve() in input_paths:
                parser.error("Output must not overwrite an input file")
        started = perf_counter()
        companies = load_companies(args.data)
        data_seconds = perf_counter() - started
        print(f"Loaded company records: {len(companies)}")
        if not queries:
            return
        engine = SearchPipeline(
            companies,
            args.method,
            args.profile,
            args.candidates,
            args.rank_only,
            args.qualify,
        )
        if args.output:
            report = {
                "method": args.method,
                "profile": args.profile,
                "top": args.top,
                "candidates": args.candidates,
                "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                "company_count": len(companies),
                "data_load_seconds": data_seconds,
                "model_index_load_seconds": engine.load_seconds,
                "configuration": engine.metadata,
                "profile_cache_reused": (
                    engine.engine.cache_hit if engine.engine else None
                ),
                "queries": [],
            }
        for query in queries:
            output = engine.search(query["text"], args.top)
            if args.output:
                report["queries"].append({"query": query, **output})
            title = query["text"]
            if args.queries:
                title = f"[{query['id']}] {title}"
            print(f"\n{title}")
            show_query_results(output, details=args.details)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False),
                encoding="utf-8",
            )
            print(f"Results saved: {args.output}")
    except (RuntimeError, OSError, ValueError) as error:
        parser.exit(1, f"Search error: {error}\n")


def show_query_results(output, details=False):
    results = output["results"]
    uncertain = output["uncertain_results"]
    if details:
        print("Parsed query:")
        print(json.dumps(output["parsed_query"], ensure_ascii=False, indent=2))
        print(f"Structured filter counts: {output['counts']}")

    label = "Qualified results" if output["qualified"] else "Ranked candidates"
    print(f"{label}: {len(results)}")
    show_results(results, details=details)

    shortlists = output.get("qualification_counts", {})
    review_count = shortlists.get("insufficient_information", len(uncertain))
    if review_count:
        print(f"Candidates needing review: {review_count}")
        if details:
            show_results(uncertain, details=True)
        else:
            print("Use --details to see why candidates need review.")


def show_results(results, details=False):
    for rank, result in enumerate(results, start=1):
        name = result["company"].get("operational_name") or "Unnamed company"
        print(f"{rank}. {name}")
        verdict = result.get("qualification")
        if details:
            score_type = result.get("score_type", "word overlap")
            print(f"   Score ({score_type}): {result['score']:.4g}")
            if result.get("matched_words"):
                print(f"   Matched words: {', '.join(result['matched_words'])}")
            checks = result.get("filter_check", {}).get("checks", [])
            missing = [
                check["field"] for check in checks if check["status"] == "unknown"
            ]
            if missing:
                print(f"   Missing or invalid filter values: {', '.join(missing)}")
        if verdict:
            print(f"   {verdict['reason']}")
            if details and verdict["evidence"]:
                quote = verdict["evidence"][0]
                preview = quote if len(quote) <= 240 else quote[:237] + "..."
                print(f"   Evidence: {preview}")


if __name__ == "__main__":
    main()
