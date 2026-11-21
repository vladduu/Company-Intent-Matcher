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


SUPPORTED_FAMILIES = (
    ({"food", "manufacturer"}, {"food", "manufacturer"}),
    ({"pharma"}, {"pharma", "manufacturer", "supplier"}),
    ({"construction"}, {"construction"}),
    ({"hr", "saas", "b2b"}, {"hr", "saas", "b2b", "supplier"}),
    ({"energy"}, {"energy", "startup", "equipment", "manufacturer", "supplier"}),
    ({"fintech"}, {"fintech", "growth", "bank_competitor"}),
    ({"ecommerce", "platform"}, {"ecommerce", "platform"}),
    ({"battery", "component"}, {"battery", "component", "manufacturer", "supplier"}),
)

MANUFACTURING = r"manufactur\w*|produc(?:e[sd]?|ing|tion)"
PROVIDER_ACTION = (
    MANUFACTURING
    + r"|develop\w*|supply|supplies|provid\w*|offer\w*|specializ\w*|engaged in"
)
CUSTOMER_CONTEXT = re.compile(
    r"\b(?:clients|customers|serves|serving|industries|sectors)\b", re.I
)


def text_values(value):
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    return []


def matching_text(pattern, values):
    return [value for value in values if re.search(pattern, value, re.I)]


class ProfileEvidence:
    def __init__(self, company):
        description = company.get("description")
        self.description = description if isinstance(description, str) else ""
        self.text = self.description.casefold()
        self.sentences = re.split(r"(?<=[.!?])\s+", self.description)
        self.offerings = text_values(company.get("core_offerings"))
        self.models = text_values(company.get("business_model"))
        self.missing = []
        self.evidence = []

    def require(self, name, proof):
        if proof:
            self.evidence.extend(proof)
        else:
            self.missing.append(name)

    def direct(self, topic, verbs=PROVIDER_ACTION):
        # A topic mentioned only as a customer market is not provider evidence.
        pattern = re.compile(rf"(?:{verbs})[^.;]{{0,160}}(?:{topic})", re.I)
        hits = []
        for sentence in self.sentences:
            match = pattern.search(sentence)
            if match and not CUSTOMER_CONTEXT.search(match.group()):
                hits.append(sentence)
        return hits

    def check_industry(self, concepts):
        if "food" in concepts:
            topic = r"food|beverages?|meat|dairy|cheese|bread|bakery|soft drinks|beer|wine|snacks"
            self.require(
                "food/beverage manufacturing", self.direct(topic, MANUFACTURING)
            )
            self.require(
                "food/beverage product offering", matching_text(topic, self.offerings)
            )
        if "pharma" in concepts:
            topic = r"pharmaceutical|medicines?|drug (?:discovery|development|manufacturing)|active pharmaceutical ingredients|peptides"
            self.require(
                "pharmaceutical development, production or supply", self.direct(topic)
            )
            self.require(
                "pharmaceutical offering", matching_text(topic, self.offerings)
            )
        if "construction" in concepts:
            self.require(
                "construction execution",
                self.direct(
                    r"construction|civil engineering|building services|infrastructure contracting"
                ),
            )
            self.require(
                "construction service offering",
                matching_text(
                    r"construction|civil engineering|general contracting",
                    self.offerings,
                ),
            )
            if re.search(
                r"construction (?:software|equipment|materials)|building materials",
                self.text,
            ) and not self.direct(
                r"construction services|construction projects|general contracting"
            ):
                self.missing.append(
                    "construction operator rather than software/equipment/materials vendor"
                )

    def check_business_model(self, concepts):
        if "hr" in concepts:
            self.require(
                "HR software provider",
                self.direct(
                    r"(?:hr|human resources|payroll)[^.;]{0,50}(?:software|platform|solutions)|software[^.;]{0,50}(?:hr|human resources|payroll)"
                ),
            )
        if "saas" in concepts:
            self.require(
                "SaaS delivery",
                matching_text(
                    r"software.as.a.service|\bsaas\b", self.models + [self.description]
                )
                or self.direct(
                    r"cloud-based[^.;]{0,60}(?:software|platform|hr|management systems)"
                ),
            )
        if "b2b" in concepts:
            self.require(
                "business customers",
                matching_text(r"business.to.business|\bb2b\b", self.models)
                or self.direct(
                    r"software[^.;]{0,80}for (?:businesses|organizations|enterprises)"
                ),
            )

    def check_energy(self, concepts):
        if "energy" in concepts:
            topic = r"renewable energy|clean energy|green energy|solar|wind (?:power|turbines|energy)|hydropower|geothermal|green hydrogen"
            self.require("clean/renewable energy provider", self.direct(topic))
            self.require("energy offering", matching_text(topic, self.offerings))
        if "startup" in concepts:
            # Age/headcount alone do not prove startup status.
            self.require(
                "explicit startup status",
                matching_text(r"\bstart-?up\b", [self.description]),
            )
        if "equipment" in concepts:
            equipment = r"turbines?|solar panels?|inverters?|photovoltaic (?:modules|panels)|generators?|electroly[sz]ers?|equipment"
            self.require("energy equipment", self.direct(equipment))

    def check_manufacturing(self, concepts):
        if "manufacturer" in concepts and "food" not in concepts:
            topic = (
                r"turbines?|solar panels?|inverters?|modules|generators?|electroly[sz]ers?|equipment"
                if "energy" in concepts
                else r"pharmaceutical|drug|battery|cathode|anode|electrolyte|separator|components"
            )
            self.require(
                "manufacturing, not just reselling/installation",
                self.direct(topic, MANUFACTURING),
            )
            if re.search(r"investment|investors|portfolio|pension", self.text):
                self.require(
                    "explicit own production rather than investment in producers",
                    self.direct(
                        topic, r"manufactures|produces|manufacturing of|production of"
                    ),
                )

    def check_fintech(self, concepts):
        if "fintech" in concepts:
            self.require(
                "financial technology provider",
                self.direct(
                    r"fintech|financial technology|digital (?:banking|payment|lending)|financial (?:platform|services)"
                )
                or matching_text(
                    r"\bfintech company\b|\bneobank\b|\bchallenger bank\b",
                    [self.description],
                ),
            )
        if "growth" in concepts:
            self.require(
                "explicit rapid growth evidence (not inferred from size)",
                matching_text(
                    r"\bfast-growing\b|\brapidly growing\b|(?:revenue|customers|users).{0,45}(?:grew|growth|increased).{0,20}\d+\s*%",
                    [self.description],
                ),
            )
        if "bank_competitor" in concepts:
            self.require(
                "bank competitor role",
                matching_text(
                    r"neobank|challenger bank|compet\w*[^.;]{0,60}(?:traditional )?banks|alternative to (?:traditional )?banks",
                    [self.description],
                ),
            )

    def check_commerce(self, concepts):
        if "ecommerce" in concepts:
            self.require(
                "operates ecommerce retail",
                matching_text(
                    r"e-commerce|ecommerce|online retail",
                    self.models + [self.description],
                ),
            )
        if "platform" in concepts:
            self.require(
                "uses a named commerce platform",
                self.direct(
                    r"(?:shopify|woocommerce|magento|bigcommerce)",
                    r"uses?|using|powered by|built on|runs? on|operates? on",
                ),
            )

    def check_battery_components(self, concepts):
        if "battery" in concepts:
            self.require(
                "electric vehicle battery production context",
                matching_text(
                    r"(?:electric vehicle|\bev\b)[^.;]{0,70}batter|batter[^.;]{0,70}(?:electric vehicle|\bev\b)",
                    [self.description],
                ),
            )
            components = r"cathode|anode|electrolyte|separator|battery.grade lithium|battery.grade graphite|battery components|battery materials"
            self.require(
                "battery input/component supply",
                self.direct(
                    components, MANUFACTURING + r"|supply|supplies|supplier of"
                ),
            )
            self.require(
                "component offering", matching_text(components, self.offerings)
            )


def check_extended_role(company, activity):
    concepts, remainder = interpret(activity)
    if not concepts:
        return None
    profile = ProfileEvidence(company)
    if remainder:
        profile.missing.append("unsupported residual wording: " + remainder)
    if not profile.description or re.search(
        r"\b(?:does not|doesn't|no longer)\b", profile.text
    ):
        profile.missing.append("affirmative company description")
    if not any(
        required <= concepts <= allowed for required, allowed in SUPPORTED_FAMILIES
    ):
        profile.missing.append("supported combination of business roles")

    profile.check_industry(concepts)
    profile.check_business_model(concepts)
    profile.check_energy(concepts)
    profile.check_manufacturing(concepts)
    profile.check_fintech(concepts)
    profile.check_commerce(concepts)
    profile.check_battery_components(concepts)

    return {
        "verdict": "insufficient_information" if profile.missing else "relevant",
        "reason": (
            "Missing evidence: " + "; ".join(profile.missing)
            if profile.missing
            else "Profile supports all recognized business-role requirements."
        ),
        "evidence": list(dict.fromkeys(profile.evidence)),
        "missing_requirements": profile.missing,
        "recognized_concepts": sorted(concepts),
        "source": "composed_role_rules_v2",
    }
