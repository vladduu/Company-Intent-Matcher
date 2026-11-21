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
        raise ValueError("Query file must be a nonempty JSON list of {id, text} objects")
    seen = set()
    for item in payload:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError("Every query needs a nonempty string id")
        if item["id"] in seen or not isinstance(item.get("text"), str) or not tokenize(item["text"]):
            raise ValueError("Query IDs must be unique and text must contain words/numbers")
        seen.add(item["id"])
    return payload


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Rank and qualify company profiles")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--query", help="One company search request")
    inputs.add_argument("--queries", type=Path, help="JSON file containing query objects with id/text")
    parser.add_argument("--output", type=Path, help="Save all results, evidence and timings as JSON")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATASET_PATH, help="Company JSONL dataset")
    parser.add_argument("--top", type=int, default=10)
    add_options(parser, default_method="rerank")
    args = parser.parse_args()
    check_options(parser, args, args.top)
    if args.query is not None and not tokenize(args.query):
        parser.error("--query must contain words or numbers")
    if args.output and not (args.query or args.queries):
        parser.error("--output requires --query or --queries")
    try:
        queries = read_queries(args.queries) if args.queries else ([{"id": "query", "text": args.query}] if args.query else [])
        if args.output and args.output.resolve() in {args.data.resolve(), args.queries.resolve() if args.queries else None}:
            parser.error("Output must not overwrite an input file")
        started = perf_counter()
        companies = load_companies(args.data)
        data_seconds = perf_counter()-started
        print(f"Loaded company records: {len(companies)}")
        if not queries:
            return
        engine = SearchPipeline(companies, args.method, args.profile, args.candidates, args.rank_only, args.qualify)
        report = {"method": args.method, "profile": args.profile, "top": args.top, "candidates": args.candidates,
                  "dataset_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
                  "company_count": len(companies), "data_load_seconds": data_seconds,
                  "model_index_load_seconds": engine.load_seconds,
                  "configuration": engine.metadata,
                  "profile_cache_reused": engine.engine.cache_hit if engine.engine else None,
                  "queries": []}
        for query in queries:
            output = engine.search(query["text"], args.top)
            report["queries"].append({"query": query, **output})
            print(f"\n{query['id']}: {query['text']}")
            print(f"Structured filter counts: {output['counts']}")
            if args.queries:
                print(f"Returned: {len(output['results'])}; qualification: {output.get('qualification_counts', 'not applied')}; seconds: {output['timings_seconds']['total']:.3f}")
                for rank, item in enumerate(output["results"], 1):
                    print(f"  {rank}. {item['company'].get('operational_name')}")
            else:
                print("Parsed query:")
                print(json.dumps(output["parsed_query"], ensure_ascii=False, indent=2))
                print("Evidence-supported candidates:" if output["qualified"] else "Ranked candidates (not qualified):")
                show_results(output["results"])
                print("\nUnknown filters or insufficient evidence:")
                show_results(output["uncertain_results"])
                if "qualification_counts" in output:
                    print(f"Qualification counts: {output['qualification_counts']}")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
            print(f"Results saved: {args.output}")
    except (RuntimeError, OSError, ValueError) as error:
        parser.exit(1, f"Search error: {error}\n")


def show_results(results):
    if not results:
        print("No candidates returned.")
        return

    reranked = results[0].get("score_type") == "reranker_logit"
    semantic = results[0].get("score_type") == "cosine_similarity"
    print("\nLocally reranked candidates (score is not a probability):" if reranked else
          "\nSemantic candidates (cosine similarity, not probability):" if semantic else
          "\nKeyword results (score = number of distinct query words found):")
    for rank, result in enumerate(results, start=1):
        name = result["company"].get("operational_name") or "Unnamed company"
        if reranked:
            print(f"{rank}. {name} | Reranker: {result['score']:.4f}")
        elif semantic:
            print(f"{rank}. {name} | Similarity: {result['score']:.4f}")
        else:
            words = ", ".join(result["matched_words"])
            print(f"{rank}. {name} | Score: {result['score']} | Matched words: {words}")
        if "qualification" in result:
            verdict = result["qualification"]
            print(f"   {verdict['verdict']}: {verdict['reason']}")
            for quote in verdict["evidence"]:
                preview = quote if len(quote) <= 240 else quote[:237] + "..."
                print(f"   Evidence: {preview}")


if __name__ == "__main__":
    main()
