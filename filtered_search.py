"""Apply structured conditions before ranking candidate profiles by keyword."""

from filters import check_filters
from keyword_search import search_companies, tokenize
from query_parser import parse_query


def search_with_filters(companies, query, top=10):
    if top < 1:
        raise ValueError("Top must be positive")
    parsed = parse_query(query)
    groups = {"pass": [], "unknown": [], "fail": []}
    for company in companies:
        verdict = check_filters(company, parsed["filters"])
        groups[verdict["status"]].append(company)

    def rank(group):
        if tokenize(parsed["activity"]):
            results = search_companies(group, parsed["activity"], top)
        else:
            results = [{"company": c, "score": 0, "matched_words": []} for c in group[:top]]
        for result in results:
            result["filter_check"] = check_filters(result["company"], parsed["filters"])
        return results

    return {"parsed_query": parsed, "results": rank(groups["pass"]),
            "uncertain_results": rank(groups["unknown"]),
            "counts": {status: len(group) for status, group in groups.items()}}
