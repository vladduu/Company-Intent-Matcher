"""Composable, explicit intent concepts and evidence checks for additional roles.

This is a bounded rule system, not a general language understanding model.
Unconsumed words prevent a positive verdict rather than dropping constraints.
"""

import re


CONCEPTS = {
    "food": r"food(?: and beverage)?|beverages?",
    "pharma": r"pharmaceuticals?|pharma|drug",
    "construction": r"construction|building contractors?",
    "hr": r"hr|human resources|payroll",
    "saas": r"saas|software.as.a.service",
    "b2b": r"b2b|business.to.business",
    "energy": r"renewable energy|clean energy|green energy",
    "startup": r"startups?|start-ups?",
    "equipment": r"equipment|hardware",
    "manufacturer": r"manufacturers?|manufacturing|manufacture|producers?|produce",
    "supplier": r"suppliers?|supply|supplies|supplying",
    "fintech": r"fintech|financial technology",
    "growth": r"fast-growing|fast growing|rapidly growing",
    "bank_competitor": r"competing with traditional banks|challenging traditional banks",
    "ecommerce": r"e-commerce|ecommerce|online retailers?",
    "platform": r"shopify-like platforms|shopify(?: or similar platforms)?|shopify-like",
    "battery": r"(?:electric vehicle|ev) batter(?:y|ies)|batter(?:y|ies) for electric vehicles",
    "component": r"(?:critical )?components?|materials?",
}
FILLER = r"\b(?:companies|company|firms|businesses|that|could|providing|provide|offering|offer|solutions|services|for|a|an|the|and|using|production|of)\b"


def interpret(activity):
    remainder = activity.casefold()
    concepts = set()
    for name, pattern in CONCEPTS.items():
        remainder, count = re.subn(r"\b(?:" + pattern + r")\b", " ", remainder)
        if count:
            concepts.add(name)
    remainder = re.sub(FILLER, " ", remainder)
    remainder = " ".join(remainder.strip(" .?!,").split())
    return concepts, remainder


def check_extended_role(company, activity):
    concepts, remainder = interpret(activity)
    if not concepts:
        return None
    description = company.get("description") or ""
    if not isinstance(description, str):
        description = ""
    raw_offers = company.get("core_offerings") or []
    if isinstance(raw_offers, str):
        raw_offers = [raw_offers]
    offers = [value for value in raw_offers if isinstance(value, str)]
    models = company.get("business_model") or []
    if isinstance(models, str):
        models = [models]
    models = [value for value in models if isinstance(value, str)]
    text = description.casefold()
    missing, evidence = [], []

    def require(name, proof):
        if proof:
            evidence.extend(proof)
        else:
            missing.append(name)

    def excerpts(pattern, values):
        return [value for value in values if re.search(pattern, value, re.I)]

    def direct(topic, verbs=r"manufactur\w*|produc(?:e[sd]?|ing|tion)|develop\w*|supply|supplies|provid\w*|offer\w*|specializ\w*|engaged in"):
        # A topic merely listed as a customer market is not provider evidence.
        pattern = rf"(?:{verbs})[^.;]{{0,160}}(?:{topic})"
        hits = []
        for sentence in re.split(r"(?<=[.!?])\s+", description):
            match = re.search(pattern, sentence, re.I)
            if match and not re.search(r"\b(?:clients|customers|serves|serving|industries|sectors)\b", match.group(), re.I):
                hits.append(sentence)
        return hits

    if remainder:
        missing.append("unsupported residual wording: " + remainder)
    if not description or re.search(r"\b(?:does not|doesn't|no longer)\b", text):
        missing.append("affirmative company description")

    # Only combinations with explicit semantics are eligible for acceptance.
    families = [
        ({"food", "manufacturer"}, {"food", "manufacturer"}),
        ({"pharma"}, {"pharma", "manufacturer", "supplier"}),
        ({"construction"}, {"construction"}),
        ({"hr", "saas", "b2b"}, {"hr", "saas", "b2b", "supplier"}),
        ({"energy"}, {"energy", "startup", "equipment", "manufacturer", "supplier"}),
        ({"fintech"}, {"fintech", "growth", "bank_competitor"}),
        ({"ecommerce", "platform"}, {"ecommerce", "platform"}),
        ({"battery", "component"}, {"battery", "component", "manufacturer", "supplier"}),
    ]
    if not any(required <= concepts <= allowed for required, allowed in families):
        missing.append("supported combination of business roles")

    if "food" in concepts:
        topic = r"food|beverages?|meat|dairy|cheese|bread|bakery|soft drinks|beer|wine|snacks"
        require("food/beverage manufacturing", direct(topic, r"manufactur\w*|produc(?:e[sd]?|ing|tion)"))
        require("food/beverage product offering", excerpts(topic, offers))
    if "pharma" in concepts:
        topic = r"pharmaceutical|medicines?|drug (?:discovery|development|manufacturing)|active pharmaceutical ingredients|peptides"
        require("pharmaceutical development, production or supply", direct(topic))
        require("pharmaceutical offering", excerpts(topic, offers))
    if "construction" in concepts:
        require("construction execution", direct(r"construction|civil engineering|building services|infrastructure contracting"))
        require("construction service offering", excerpts(r"construction|civil engineering|general contracting", offers))
        if re.search(r"construction (?:software|equipment|materials)|building materials", text) and not direct(r"construction services|construction projects|general contracting"):
            missing.append("construction operator rather than software/equipment/materials vendor")
    if "hr" in concepts:
        require("HR software provider", direct(r"(?:hr|human resources|payroll)[^.;]{0,50}(?:software|platform|solutions)|software[^.;]{0,50}(?:hr|human resources|payroll)"))
    if "saas" in concepts:
        require("SaaS delivery", excerpts(r"software.as.a.service|\bsaas\b", models + [description]) or
                direct(r"cloud-based[^.;]{0,60}(?:software|platform|hr|management systems)"))
    if "b2b" in concepts:
        require("business customers", excerpts(r"business.to.business|\bb2b\b", models) or direct(r"software[^.;]{0,80}for (?:businesses|organizations|enterprises)"))
    if "energy" in concepts:
        topic = r"renewable energy|clean energy|green energy|solar|wind (?:power|turbines|energy)|hydropower|geothermal|green hydrogen"
        require("clean/renewable energy provider", direct(topic))
        require("energy offering", excerpts(topic, offers))
    if "startup" in concepts:
        # Age/headcount alone do not prove startup status.
        require("explicit startup status", excerpts(r"\bstart-?up\b", [description]))
    if "equipment" in concepts:
        equipment = r"turbines?|solar panels?|inverters?|photovoltaic (?:modules|panels)|generators?|electroly[sz]ers?|equipment"
        require("energy equipment", direct(equipment))
    if "manufacturer" in concepts and "food" not in concepts:
        topic = r"turbines?|solar panels?|inverters?|modules|generators?|electroly[sz]ers?|equipment" if "energy" in concepts else r"pharmaceutical|drug|battery|cathode|anode|electrolyte|separator|components"
        require("manufacturing, not just reselling/installation", direct(topic, r"manufactur\w*|produc(?:e[sd]?|ing|tion)"))
        if re.search(r"investment|investors|portfolio|pension", text):
            require("explicit own production rather than investment in producers",
                    direct(topic, r"manufactures|produces|manufacturing of|production of"))
    if "fintech" in concepts:
        require("financial technology provider", direct(r"fintech|financial technology|digital (?:banking|payment|lending)|financial (?:platform|services)") or
                excerpts(r"\bfintech company\b|\bneobank\b|\bchallenger bank\b", [description]))
    if "growth" in concepts:
        require("explicit rapid growth evidence (not inferred from size)", excerpts(r"\bfast-growing\b|\brapidly growing\b|(?:revenue|customers|users).{0,45}(?:grew|growth|increased).{0,20}\d+\s*%", [description]))
    if "bank_competitor" in concepts:
        require("bank competitor role", excerpts(r"neobank|challenger bank|compet\w*[^.;]{0,60}(?:traditional )?banks|alternative to (?:traditional )?banks", [description]))
    if "ecommerce" in concepts:
        require("operates ecommerce retail", excerpts(r"e-commerce|ecommerce|online retail", models + [description]))
    if "platform" in concepts:
        require("uses a named commerce platform", direct(r"(?:shopify|woocommerce|magento|bigcommerce)", r"uses?|using|powered by|built on|runs? on|operates? on"))
    if "battery" in concepts:
        require("electric vehicle battery production context", excerpts(r"(?:electric vehicle|\bev\b)[^.;]{0,70}batter|batter[^.;]{0,70}(?:electric vehicle|\bev\b)", [description]))
        components = r"cathode|anode|electrolyte|separator|battery.grade lithium|battery.grade graphite|battery components|battery materials"
        require("battery input/component supply", direct(components, r"manufactur\w*|produc(?:e[sd]?|ing|tion)|supply|supplies|supplier of"))
        require("component offering", excerpts(components, offers))
    return {"verdict": "insufficient_information" if missing else "relevant",
            "reason": "Missing evidence: " + "; ".join(missing) if missing else "Profile supports all recognized business-role requirements.",
            "evidence": list(dict.fromkeys(evidence)), "missing_requirements": missing,
            "recognized_concepts": sorted(concepts), "source": "composed_role_rules_v2"}
