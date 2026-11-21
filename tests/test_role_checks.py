import unittest
from role_checks import role_check, apply_role_checks
from query_parser import parse_query


class RoleTests(unittest.TestCase):
    def test_external_service_and_internal_network(self):
        yes = {
            "description": "The firm provides freight forwarding services to clients."
        }
        no = {
            "description": "The firm manufactures tools and operates its own logistics network."
        }
        self.assertEqual(role_check(yes, "logistics")["verdict"], "relevant")
        self.assertEqual(role_check(no, "logistics")["verdict"], "not_relevant")
        negated = {
            "description": "The firm does not provide freight forwarding services."
        }
        self.assertNotEqual(role_check(negated, "logistics")["verdict"], "relevant")

    def test_supplier_is_not_customer_or_equipment_vendor(self):
        software = {
            "description": "The firm provides freight forwarding software and equipment."
        }
        self.assertNotEqual(role_check(software, "logistics")["verdict"], "relevant")
        customer = {
            "description": "A cosmetics manufacturer using packaging for its beauty products.",
            "core_offerings": ["Cosmetic Manufacturing"],
        }
        query = "that could supply packaging materials for a direct-to-consumer cosmetics brand"
        self.assertNotEqual(role_check(customer, query)["verdict"], "relevant")

    def test_extra_constraints_are_not_silently_accepted(self):
        company = {"description": "A software development company."}
        self.assertEqual(role_check(company, "software")["verdict"], "relevant")
        self.assertEqual(
            role_check(company, "software founded after 2018")["verdict"],
            "insufficient_information",
        )

    def test_missing_description_and_filter_only(self):
        self.assertEqual(
            role_check({}, "logistics")["verdict"], "insufficient_information"
        )
        self.assertEqual(role_check({}, "")["verdict"], "relevant")

    def test_software_engineering_is_a_provider_role(self):
        company = {
            "description": "A software engineering company providing services to clients."
        }
        self.assertEqual(role_check(company, "software")["verdict"], "relevant")
        company = {
            "description": "A manufacturer uses software development tools for internal operations."
        }
        self.assertNotEqual(role_check(company, "software")["verdict"], "relevant")

    def test_names_do_not_determine_qualification(self):
        for name in ("Postal Logistics", "Unrelated Name", ""):
            company = {
                "operational_name": name,
                "description": "A firm provides parcel delivery to external clients.",
            }
            self.assertEqual(role_check(company, "logistics")["verdict"], "relevant")

    def test_internal_handling_is_not_external_service(self):
        company = {
            "description": "A manufacturer provides cargo handling for its own products."
        }
        self.assertNotEqual(role_check(company, "logistics")["verdict"], "relevant")

    def test_query_variants_have_identical_parse(self):
        self.assertEqual(
            parse_query("Logistic companies in Romania"),
            parse_query("Logistics companies in Romania"),
        )

    def test_qualifies_before_top_and_keeps_unknown_separate(self):
        rejected = {"company": {"description": "A retailer of tools."}, "score": 9}
        accepted = {
            "company": {
                "description": "It provides postal services and parcel delivery."
            },
            "score": -8,
        }
        output = {
            "parsed_query": {"activity": "logistics"},
            "results": [rejected, accepted],
            "uncertain_results": [accepted],
        }
        result = apply_role_checks(output, 10)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(len(result["uncertain_results"]), 1)
        self.assertEqual(len(result["rejected_results"]), 1)
        self.assertEqual(result["results"][0]["score"], -8)
        evidence = result["results"][0]["qualification"]["evidence"]
        self.assertEqual(evidence, [accepted["company"]["description"]])
