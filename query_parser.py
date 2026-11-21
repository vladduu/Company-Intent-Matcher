"""Small English rule parser; residual text still needs semantic interpretation."""

import re


COUNTRIES = {"romania": "ro", "germany": "de", "france": "fr",
             "united states": "us", "usa": "us", "switzerland": "ch",
             "united kingdom": "gb", "uk": "gb", "spain": "es",
             "italy": "it", "netherlands": "nl", "norway": "no",
             "sweden": "se", "denmark": "dk", "finland": "fi"}
COMPARISONS = {"more than": ">", "over": ">", "greater than": ">",
               "fewer than": "<", "less than": "<", "under": "<",
               "at least": ">=", "at most": "<=", "exactly": "=="}

# Explicit project scope, not EU membership. Includes Russia, Turkey and Cyprus
# by country code; primary-address data cannot distinguish their continental parts.
REGIONS = {
    "europe": sorted("al ad at by be ba bg hr cy cz dk ee fi fr de gr hu is ie it lv li lt lu mt md mc me nl mk no pl pt ro ru sm rs sk si es se ch tr ua gb va".split()),
    "scandinavia": ["dk", "no", "se"],
    "nordic countries": ["dk", "fi", "is", "no", "se"],
}


def parse_query(query):
    text = " ".join(query.casefold().strip().rstrip(".?!").split())
    if not text:
        raise ValueError("Query cannot be empty")
    conditions = []
    warnings = []
    if re.search(r"\b(clients|customers|serving|operating|whose|that have)\b", text):
        return {"activity": text, "filters": [], "warnings": [
            "Relationship or operating-location wording is outside this parser's supported grammar; no filters applied."
        ]}
    # Avoid turning unsupported Boolean/negated expressions into hard exclusions.
    if re.search(r"\b(not|except|excluding|without|or|between)\b", text):
        return {"activity": text, "filters": [], "warnings": [
            "Negation, alternatives or ranges require further interpretation; no filters applied."
        ]}

    public = re.match(r"^(publicly traded|privately held|public|private)\s+(?!sector\b)", text)
    if public:
        conditions.append({"field": "is_public", "operator": "==",
                           "value": public.group(1) in {"public", "publicly traded"}})
        text = text[public.end():]

    countries = "|".join(sorted(set(COUNTRIES) | set(REGIONS), key=len, reverse=True))
    country_pattern = rf"\b(?:based in|located in|in)\s+(?:the\s+)?({countries})(?=$|\s+(?:with|and|founded|established)\b)"
    def extract_country(match):
        location = match.group(1)
        conditions.append({"field": "country_code", "operator": "in" if location in REGIONS else "==",
                           "value": list(REGIONS[location]) if location in REGIONS else COUNTRIES[location]})
        return " "
    # Only trailing location clauses: 'suppliers for clients in Romania' is ambiguous.
    if not re.search(r"\b(clients|customers|serving|operating|markets|suppliers for)\b", text):
        text = re.sub(country_pattern, extract_country, text)

    comparisons = "|".join(COMPARISONS)
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    employee_pattern = rf"\b(?:with|and)\s+({comparisons})\s+({number})\s+employees\b"
    def extract_employees(match):
        conditions.append({"field": "employee_count", "operator": COMPARISONS[match.group(1)],
                           "value": int(match.group(2).replace(",", ""))})
        return " "
    text = re.sub(employee_pattern, extract_employees, text)

    # Revenue values are USD in the dataset. Other currencies remain unresolved.
    amount = rf"({number}(?:\.\d+)?)\s*(billion|million|thousand|bn|[kmb])?"
    clause_end = r"(?=\s*$|\s+(?:and|with|in|founded|established)\b)"
    revenue_pattern = (rf"\b(?:(?:with|and)\s+)?(?:annual\s+)?revenue\s+({comparisons})\s+"
                       rf"(?:\$\s*|usd\s+)?{amount}(?:\s+(?:usd|dollars))?{clause_end}")
    def extract_revenue(match):
        scale = {None: 1, "thousand": 1000, "k": 1000, "million": 1000000,
                 "m": 1000000, "billion": 1000000000, "bn": 1000000000, "b": 1000000000}
        from decimal import Decimal
        value = Decimal(match.group(2).replace(",", "")) * scale[match.group(3)]
        conditions.append({"field": "revenue", "operator": COMPARISONS[match.group(1)],
                           "value": int(value) if value == int(value) else float(value)})
        return " "
    text = re.sub(revenue_pattern, extract_revenue, text)
    year_pattern = rf"\b(?:(?:with|and)\s+)?(?:founded|established)\s+(after|before|since|in)\s+([1-9]\d{{3}}){clause_end}"
    def extract_year(match):
        conditions.append({"field": "year_founded", "operator": {"after": ">", "before": "<", "since": ">=", "in": "=="}[match.group(1)],
                           "value": int(match.group(2))})
        return " "
    text = re.sub(year_pattern, extract_year, text)
    # The residual is search text, not a claim that we understood its full meaning.
    text = re.sub(r"\b(find|companies|company)\b", " ", text)
    text = " ".join(text.split()).strip(" ,")
    text = re.sub(r"^(?:and\s+)+|(?:\s+and)+$", "", text).strip()
    # Normalize an equivalent activity variant for both embedding and reranking stages.
    text = re.sub(r"\blogistic\b", "logistics", text)
    if re.search(r"\b(employees|public|private|revenue|founded|established|in|not|or|with)\b", text):
        warnings.append("Residual text may contain unsupported constraints; these were not applied as filters.")
    warnings.append("Activity and business role are still checked by keyword overlap, not semantic qualification.")
    return {"activity": text, "filters": conditions, "warnings": warnings}
