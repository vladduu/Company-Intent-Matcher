"""Repeat the keyword baseline evaluation using explicitly labeled profiles."""

import hashlib
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from data_loader import DEFAULT_DATASET_PATH, load_companies
from pipeline import SearchPipeline
from cli_options import add_options, check_options


def company_id(company):
    text = json.dumps(company, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Evaluate one search method on development queries")
    add_options(parser, default_method="keyword")
    parser.add_argument("--output", type=Path, help="Save results and profiles for manual review")
    args = parser.parse_args()
    check_options(parser, args, 10)
    path = Path(__file__).resolve().parent / "evaluation" / "development_cases.json"
    evaluation = json.loads(path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(DEFAULT_DATASET_PATH.read_bytes()).hexdigest()
    if digest != evaluation["dataset_sha256"]:
        raise ValueError("Dataset changed; review the evaluation cases before comparing results.")

    companies = load_companies()
    try:
        engine = SearchPipeline(companies, args.method, args.profile, args.candidates, args.rank_only, args.qualify)
    except (RuntimeError, OSError, ValueError) as error:
        parser.exit(1, f"Search initialization error: {error}\n")
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
    report = {"method": args.method, "profile": args.profile, "qualified": args.qualify or (args.method == "rerank" and not args.rank_only), "candidates": args.candidates,
              "label_status": "assistant-proposed, pending human review",
              "model_index_load_seconds": engine.load_seconds, "configuration": engine.metadata, "queries": []}
    for query in evaluation["queries"]:
        try:
            output = engine.search(query["text"], 10)
        except (RuntimeError, OSError, ValueError) as error:
            parser.exit(1, f"Search error: {error}\n")
        results = output["results"]
        print(f"\nStructured filter counts: {output['counts']}; unknown candidates excluded from passing list")
        counts = Counter(labels.get((query["id"], company_id(r["company"])), "unjudged") for r in results)
        print(f"\n{query['id']}: {query['text']}")
        print(f"Returned: {len(results)}; relevant: {counts['relevant']}; "
              f"not relevant: {counts['not_relevant']}; "
              f"insufficient information: {counts['insufficient_information']}; "
              f"unjudged: {counts['unjudged']}")
        print(f"Confirmed-relevant@10: {counts['relevant'] / 10:.2f}")
        if counts["unjudged"] == 0 and counts["insufficient_information"] == 0 and results:
            print(f"Proposed-label precision among returned: {counts['relevant'] / len(results):.2f} (development only)")
        judged = counts['relevant'] + counts['not_relevant']
        print(f"Decisive label coverage: {judged}/{len(results)} returned; proposed labels still need review")
        report["queries"].append({"query": query, "counts": dict(counts), "timings_seconds": output["timings_seconds"],
            "qualification_counts": output.get("qualification_counts") if args.method != "keyword" else None,
            "review_candidates": output.get("review_candidates", []) if args.method != "keyword" else [],
            "results": [dict(r, company_id=company_id(r["company"]),
                             evaluation_label=labels.get((query["id"], company_id(r["company"])), "unjudged"))
                        for r in results],
            "uncertain_results": output["uncertain_results"] if args.method != "keyword" else [],
            "rejected_results": output.get("rejected_results", []) if args.method != "keyword" else []})
        for rank, result in enumerate(results, 1):
            company = result["company"]
            label = labels.get((query["id"], company_id(company)), "unjudged")
            print(f"  {rank}. {company.get('operational_name')} | {label}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Review report saved: {args.output}")


if __name__ == "__main__":
    main()
