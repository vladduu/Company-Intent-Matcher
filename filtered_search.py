"""Apply structured conditions before ranking candidate profiles by keyword."""

from filters import check_filters
from keyword_search import search_companies, tokenize
from query_parser import parse_query


def search_with_filters(companies, query, top=10):
    if top < 1:
        raise ValueError("Top must be positive")
    parsed = parse_query(query)
    activity = parsed["activity"]
    has_keywords = bool(tokenize(activity))
    groups = {"pass": [], "unknown": []}
    counts = {"pass": 0, "unknown": 0, "fail": 0}
    checks_by_company = {}
    for company in companies:
        verdict = check_filters(company, parsed["filters"])
        status = verdict["status"]
        counts[status] += 1
        if status != "fail":
            groups[status].append(company)
            checks_by_company[id(company)] = verdict

    def rank(group):
        if has_keywords:
            results = search_companies(group, activity, top, normalize_variants=True)
        else:
            results = []
            for company in group[:top]:
                results.append({"company": company, "score": 0, "matched_words": []})
        for result in results:
            result["filter_check"] = checks_by_company[id(result["company"])]
        return results

    return {
        "parsed_query": parsed,
        "results": rank(groups["pass"]),
        "uncertain_results": rank(groups["unknown"]),
        "counts": counts,
    }
