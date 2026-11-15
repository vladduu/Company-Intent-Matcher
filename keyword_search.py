"""A simple keyword baseline for company search."""

import re


WORD_VARIANTS = {
    "logistic": "logistics",
    "cosmetics": "cosmetic",
    "pharmaceuticals": "pharmaceutical",
    "manufacturers": "manufacturer",
    "suppliers": "supplier",
    "distributors": "distributor",
    "services": "service",
    "products": "product",
    "materials": "material",
    "components": "component",
    "batteries": "battery",
    "vehicles": "vehicle",
    "solutions": "solution",
}


def tokenize(text):
    """Return distinct lowercase words, ignoring punctuation and underscores."""
    return set(re.findall(r"[^\W_]+", text.casefold()))


def normalize_words(words):
    """Map explicitly supported variants to one term, without stripping suffixes."""
    return {WORD_VARIANTS.get(word, word) for word in words}


def build_company_text(company):
    parts = []
    for field in ("description", "core_offerings", "business_model"):
        value = company.get(field)
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(item for item in value if isinstance(item, str))
    return " ".join(parts)


def search_companies(companies, query, top=10, normalize_variants=False):
    """Rank by distinct query words found; preserve input order for ties."""
    query_words = tokenize(query)
    if normalize_variants:
        query_words = normalize_words(query_words)
    if not query_words:
        raise ValueError("Query must contain at least one word or number.")
    if top < 1:
        raise ValueError("Top must be a positive integer.")

    results = []
    for company in companies:
        company_words = tokenize(build_company_text(company))
        if normalize_variants:
            company_words = normalize_words(company_words)
        matched_words = sorted(query_words & company_words)
        if matched_words:
            results.append({
                "company": company,
                "score": len(matched_words),
                "matched_words": matched_words,
            })

    results.sort(key=lambda result: result["score"], reverse=True)
    return results[:top]
