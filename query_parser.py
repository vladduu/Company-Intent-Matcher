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

    countries = "|".join(sorted(COUNTRIES, key=len, reverse=True))
    country_pattern = rf"\b(?:based in|located in|in)\s+(?:the\s+)?({countries})(?=$|\s+with\b|\s+and\b)"
    def extract_country(match):
        conditions.append({"field": "country_code", "operator": "==", "value": COUNTRIES[match.group(1)]})
        return " "
    # Only trailing location clauses: 'suppliers for clients in Romania' is ambiguous.
    if not re.search(r"\b(clients|customers|serving|operating|markets|suppliers for)\b", text):
        text = re.sub(country_pattern, extract_country, text)

    comparisons = "|".join(COMPARISONS)
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    employee_pattern = rf"\bwith\s+({comparisons})\s+({number})\s+employees\b"
    def extract_employees(match):
        conditions.append({"field": "employee_count", "operator": COMPARISONS[match.group(1)],
                           "value": int(match.group(2).replace(",", ""))})
        return " "
    text = re.sub(employee_pattern, extract_employees, text)
    # The residual is search text, not a claim that we understood its full meaning.
    text = re.sub(r"\b(find|companies|company)\b", " ", text)
    text = " ".join(text.split()).strip(" ,")
    if re.search(r"\b(employees|public|private|revenue|founded|in|not|or|with)\b", text):
        warnings.append("Residual text may contain unsupported constraints; these were not applied as filters.")
    warnings.append("Activity and business role are still checked by keyword overlap, not semantic qualification.")
    return {"activity": text, "filters": conditions, "warnings": warnings}
