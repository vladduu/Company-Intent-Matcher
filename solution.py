"""Entry point for the Intent Qualification challenge solution."""

import argparse
import json
import sys

from data_loader import load_companies
from keyword_search import search_companies, tokenize
from filtered_search import search_with_filters
from qualification import Qualifier, add_options, check_options


def main():
    # Preserve company names with diacritics when output is redirected on Windows.
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Rank company profiles using keyword or semantic retrieval.")
    parser.add_argument("--query", help="Company search request")
    parser.add_argument("--top", type=int, default=10, help="Maximum results (default: 10)")
    parser.add_argument("--method", choices=("keyword", "filters", "semantic", "hybrid", "rerank"), default="keyword")
    add_options(parser)
    args = parser.parse_args()
    check_options(parser, args, args.top)
    if args.top < 1:
        parser.error("--top must be a positive integer")
    if args.query is not None and not tokenize(args.query):
        parser.error("--query must contain at least one word or number")

    companies = load_companies()
    print(f"Loaded company records: {len(companies)}")
    if args.query is None:
        return

    if args.method != "keyword":
        if args.method == "filters":
            output = search_with_filters(companies, args.query, args.top)
        else:
            from semantic_search import SemanticSearch
            try:
                qualifier = Qualifier() if args.qualify else None
                engine = SemanticSearch(companies, profile_mode=args.profile)
                reranker = None
                if args.method == "rerank":
                    from reranker import LocalReranker
                    reranker = LocalReranker()
                output = engine.search(args.query, args.candidates if qualifier or args.method == "rerank" else args.top,
                                       hybrid=args.method in ("hybrid", "rerank"))
                if reranker:
                    output = reranker.apply(output, args.query, args.candidates)
                    if not args.rank_only:
                        from role_checks import apply_role_checks
                        output = apply_role_checks(output, args.top)
                    else:
                        output["results"] = output["results"][:args.top]
                        output["uncertain_results"] = output["uncertain_results"][:args.top]
                if qualifier:
                    output = qualifier.apply(output, args.query, args.top)
            except (RuntimeError, OSError, ValueError) as error:
                parser.exit(1, f"Semantic search error: {error}\n")
            print(f"Profile embedding cache reused: {engine.cache_hit}")
        print("Parsed query:")
        print(json.dumps(output["parsed_query"], indent=2, ensure_ascii=False))
        print(f"Structured filter counts: {output['counts']}")
        if "reranked_count" in output:
            print(f"Locally reranked candidates: {output['reranked_count']}")
        if "qualification_counts" in output:
            print(f"Qualification counts: {output['qualification_counts']}")
        print("Candidates supported by qualification evidence:" if "qualification_counts" in output else
              "Candidates passing extracted filters (full intent is not yet qualified):")
        show_results(output["results"])
        print("\nCandidates with unknown filters or insufficient qualification evidence:")
        show_results(output["uncertain_results"])
        if "qualification_counts" in output:
            print("\nRejected by qualification:")
            show_results(output["rejected_results"])
        return

    results = search_companies(companies, args.query, args.top)
    show_results(results)


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
