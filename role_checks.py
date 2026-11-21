"""Conservative, bounded role checks. No company names or evaluation labels used."""

import re
from collections import Counter


def verdict(label, reason, evidence=()):
    return {"verdict": label, "reason": reason, "evidence": list(evidence),
            "source": "local_role_rules_v1"}


def role_check(company, activity):
    """Only explicitly supported residual intents can receive a positive verdict."""
    activity = " ".join(activity.casefold().strip(" .?!").split())
    if re.fullmatch(r"software (?:development|engineering|providers|developers)", activity):
        activity = "software"
    if re.fullmatch(r"(?:logistics (?:providers|service providers)|providers of logistics services)", activity):
        activity = "logistics"
    if re.fullmatch(r"(?:cosmetics? packaging suppliers|packaging suppliers for cosmetics? brands)", activity):
        activity = "supply packaging materials for a cosmetics brand"
    if not activity:
        return verdict("relevant", "All extracted structured conditions passed; no residual activity.")
    description = company.get("description")
    if not isinstance(description, str) or not description.strip():
        return verdict("insufficient_information", "A description is required to establish the company's role.")
    offerings = company.get("core_offerings") or []
    if isinstance(offerings, str):
        offerings = [offerings]
    offerings = [s for s in offerings if isinstance(s, str)]
    text = description.casefold()
    unknown = verdict("insufficient_information", "The profile does not explicitly establish the requested provider role.", [description])
    if re.search(r"\b(?:does not|doesn't|no longer)\b", text):
        return verdict("insufficient_information", "Negated activity needs review before accepting a provider role.", [description])
    if re.fullmatch(r"(?:logistics?|logistics? services|freight transportation|freight forwarding)", activity):
        if re.search(r"\b(?:software|equipment|systems)\b", text) and not re.search(r"postal services|parcel delivery|cargo handling", text):
            return unknown
        # Infrastructure access and property leasing do not establish freight operation.
        if re.search(r"railway infrastructure|logistics facilities|facility leasing|facilities.*leas", text):
            return verdict("insufficient_information", "Infrastructure or facility provision does not confirm operating logistics services.", [description])
        direct = re.search(
            r"(?:provid\w*|offer\w*|specializ\w*|engaged in|operates as)[^.]{0,180}"
            r"(?:parcel delivery|postal services|cargo handling|freight forwarding|freight transport|warehousing services|logistics services)", text)
        internal = re.search(r"(?:own|internal) (?:operations|products|goods)|to support its operations", text)
        if direct and not internal and not re.search(r"\b(?:does not|doesn't|no longer|not provide|not offer)\b", text):
            return verdict("relevant", "Description explicitly establishes postal, freight, cargo or warehousing services.", [description])
        # Ambiguous offering lists are not sufficient to override the description.
        ambiguous = any(re.search(r"logistics|warehouse|transport.*services|storage.*services", s, re.I) for s in offerings)
        if ambiguous or re.search(r"transport and storage services|physical movement", text):
            return unknown
        if re.search(r"real estate|software company|manufactur|production|refining|retail|wholesale|distribut|consulting|natural gas", text):
            return verdict("not_relevant", "Description establishes a different business role; it does not offer the requested logistics service.", [description])
        return unknown
    if activity == "software":
        software_offer = [s for s in offerings if re.search(
            r"(?:software|application).*(?:develop|publish)|(?:develop|publish).*software", s, re.I)]
        explicit = re.search(r"software (?:development|engineering|company|publisher)|develop\w*[^.]{0,50}software|provid\w*[^.]{0,60}software (?:solutions|products|services)", text)
        internal = re.search(r"(?:uses?|using|internal|in-house)[^.]{0,50}software", text)
        if explicit and not internal and not re.search(r"\b(?:does not|doesn't|no longer)\b", text):
            return verdict("relevant", "Description establishes software development or software provision; services firms are included.", [description])
        if software_offer and re.search(r"information technology|it consulting|technology solutions|digital|software", text) and not internal:
            return verdict("relevant", "Technology-provider description is corroborated by explicit software-development offerings.", [description, software_offer[0]])
        return unknown
    # Deliberately narrow grammar: extra constraints must not disappear unnoticed.
    packaging = re.fullmatch(
        r"(?:that could supply|supplying|supply|providing) packaging materials for (?:a )?(?:direct-to-consumer )?cosmetics? brand", activity)
    if packaging:
        has_market = re.search(r"cosmetic|beauty|skincare|skin care|personal care", text)
        has_product = re.search(r"packaging|packing paper|bottles|jars|containers", text)
        provides = re.search(r"manufactur|supply|suppli|production|provid|offering|offers|engaged in", text)
        product_offer = [s for s in offerings if re.search(r"packaging|packing paper|bottle|jar|container", s, re.I)
                         and re.search(r"manufactur|supply|wholesale|retail|distribution|production", s, re.I)]
        if has_market and has_product and provides and product_offer and not re.search(r"\b(?:does not|doesn't|no longer)\b", text):
            return verdict("relevant", "Profile establishes packaging products supplied to cosmetics/personal-care markets; commercial suitability still needs validation.", [description, product_offer[0]])
        return unknown
    from intent_roles import check_extended_role
    extended = check_extended_role(company, activity)
    if extended is not None:
        return extended
    return verdict("insufficient_information", "Residual intent is outside the local role rules; ranked candidate requires review.", [description])


def apply_role_checks(output, top):
    """Qualify the entire ranked shortlist BEFORE applying the final result limit."""
    accepted, unknown, rejected = [], [], []
    activity = output["parsed_query"]["activity"]
    for item in output["results"]:
        judgment = role_check(item["company"], activity)
        updated = dict(item, qualification=judgment)
        {"relevant": accepted, "insufficient_information": unknown,
         "not_relevant": rejected}[judgment["verdict"]].append(updated)
    for item in output["uncertain_results"]:
        unknown.append(dict(item, qualification=verdict(
            "insufficient_information", "At least one structured condition is unknown; cannot accept this candidate.")))
    counts = Counter({"relevant": len(accepted), "insufficient_information": len(unknown), "not_relevant": len(rejected)})
    return dict(output, results=accepted[:top], uncertain_results=unknown[:top],
                rejected_results=rejected, qualification_counts=dict(counts),
                review_candidates=unknown, accepted_count=len(accepted))
