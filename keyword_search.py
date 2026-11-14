"""A simple keyword baseline for company search."""

import re


def tokenize(text):
    """Return distinct lowercase words, ignoring punctuation and underscores."""
    return set(re.findall(r"[^\W_]+", text.casefold()))


def build_company_text(company):
    parts = []
    for field in ("description", "core_offerings", "business_model"):
        value = company.get(field)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(item for item in value if isinstance(item, str))
    return " ".join(parts)


def search_companies(companies, query, top=10):
    """Rank by distinct query words found; preserve input order for ties."""
    query_words = tokenize(query)
    if not query_words:
        raise ValueError("Query must contain at least one word or number.")
    if top < 1:
        raise ValueError("Top must be a positive integer.")

    results = []
    for company in companies:
        company_words = tokenize(build_company_text(company))
        matched_words = sorted(query_words & company_words)
        if matched_words:
            results.append({
                "company": company,
                "score": len(matched_words),
                "matched_words": matched_words,
            })

    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:top]
