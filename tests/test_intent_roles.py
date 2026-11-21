import unittest

from query_parser import parse_query
from role_checks import role_check


class IntentRoleTests(unittest.TestCase):
    def check(self, query, description, offers=(), models=()):
        return role_check({"description": description, "core_offerings": list(offers),
                           "business_model": list(models)}, parse_query(query)["activity"])

    def test_supported_positive_roles(self):
        cases = [
            ("Food and beverage manufacturers in France", "The firm produces dairy food and cheese.", ["Cheese manufacturing"], []),
            ("Construction companies in the United States with revenue over $50 million", "The firm provides construction services for buildings.", ["Building construction"], []),
            ("Pharmaceutical companies in Switzerland", "The firm develops pharmaceutical products.", ["Pharmaceutical manufacturing"], []),
            ("B2B SaaS companies providing HR solutions in Europe", "The firm develops HR software for businesses.", ["HR software"], ["Business-to-Business", "Software-as-a-Service"]),
            ("Clean energy startups founded after 2018 with fewer than 200 employees", "This startup develops clean energy solutions.", ["Solar power solutions"], []),
            ("Renewable energy equipment manufacturers in Scandinavia", "The firm manufactures solar panels and develops renewable energy systems.", ["Solar panel manufacturing"], []),
            ("Companies that manufacture or supply critical components for electric vehicle battery production", "The firm supplies cathode materials for electric vehicle battery production.", ["Cathode manufacturing"], []),
            ("E-commerce companies using Shopify or similar platforms", "The firm operates an e-commerce store powered by Shopify.", [], []),
            ("Fast-growing fintech companies competing with traditional banks in Europe", "A fast-growing fintech company operates as a challenger bank.", [], []),
        ]
        for query, description, offers, models in cases:
            with self.subTest(query=query):
                result = self.check(query, description, offers, models)
                self.assertEqual(result["verdict"], "relevant", result)

    def test_missing_mandatory_evidence_is_not_guessed(self):
        cases = [
            ("Clean energy startups founded after 2018 with fewer than 200 employees", "The firm develops solar panels.", ["Solar panel manufacturing"], []),
            ("Fast-growing fintech companies competing with traditional banks in Europe", "The fintech company develops digital payment services with banks.", [], []),
            ("E-commerce companies using Shopify or similar platforms", "The company operates an e-commerce store.", [], []),
            ("B2B SaaS companies providing HR solutions in Europe", "The firm develops HR software for businesses.", [], ["Business-to-Business"]),
            ("Renewable energy equipment manufacturers in Scandinavia", "The firm installs solar panels and provides renewable energy services.", ["Solar panel installation"], []),
            ("Companies that manufacture or supply critical components for electric vehicle battery production", "The firm sells electric vehicles and uses battery systems.", ["Electric vehicle sales"], []),
        ]
        for query, description, offers, models in cases:
            with self.subTest(query=query):
                self.assertEqual(self.check(query, description, offers, models)["verdict"], "insufficient_information")

    def test_customer_industry_is_not_provider_role(self):
        result = self.check("Pharmaceutical companies", "The firm provides software to customers in the pharmaceutical industry.", ["Pharmaceutical software"])
        self.assertNotEqual(result["verdict"], "relevant")
        result = self.check("Food and beverage manufacturers", "The firm manufactures equipment for clients in the food industry.", ["Food machinery"])
        self.assertNotEqual(result["verdict"], "relevant")

    def test_unknown_constraints_and_negation_are_retained(self):
        for query in ["Pharmaceutical companies certified by FDA", "Construction companies without government contracts", "Food manufacturers in Japan"]:
            self.assertNotEqual(self.check(query, "The firm produces pharmaceutical food and provides construction services.", ["Pharmaceutical food construction"])["verdict"], "relevant")

    def test_reformulations_use_same_concepts(self):
        for query in ["Beverage producers in France", "Food manufacturing in France"]:
            self.assertEqual(self.check(query, "The firm produces food and beverages.", ["Beverage manufacturing"])["verdict"], "relevant")
        for query in ["Logistics providers in Romania", "Providers of logistics services in Romania"]:
            self.assertEqual(self.check(query, "The firm provides parcel delivery services.")["verdict"], "relevant")

    def test_platform_provider_is_not_platform_user(self):
        result = self.check("E-commerce companies using Shopify or similar platforms", "The firm develops e-commerce tools for Shopify merchants.")
        self.assertNotEqual(result["verdict"], "relevant")

    def test_products_do_not_imply_production(self):
        result = self.check("Renewable energy equipment manufacturers in Scandinavia",
                            "The firm provides renewable energy products such as solar panels.",
                            ["Solar panel retail"])
        self.assertNotEqual(result["verdict"], "relevant")
        result = self.check("Renewable energy equipment manufacturers",
                            "The firm specializes in investment in renewable energy manufacturing, wind turbines and pension savings.",
                            ["Wind turbines"])
        self.assertNotEqual(result["verdict"], "relevant")
        result = self.check("Food and beverage manufacturers", "The firm offers food products to retailers.", ["Food supply"])
        self.assertNotEqual(result["verdict"], "relevant")
