# Development evaluation

Run from the project root:

```powershell
python evaluate.py --method keyword
python evaluate.py --method semantic --profile description
python evaluate.py --method rerank --profile description
```

`development_cases.json` contains 64 proposed judgments across three challenge
queries. The pool includes keyword baseline results, additional relevant examples,
and profiles inspected during development of the full pipeline. The judgments
were prepared with assistant help from the supplied profiles and are pending human
review. Review the evidence and reason for each case before using the numbers as
final quality claims.
Set `review_status` to `reviewed_by_user` only after actually reviewing a case.

## Judgment rules

- `relevant`: the supplied evidence supports all required conditions.
- `not_relevant`: a required field contradicts the query or the described business
  clearly has a different role. This is a profile-based judgment, not a claim
  about all possible real-world activities of the company.
- `insufficient_information`: a necessary fact or role is ambiguous or unavailable.

For q1, Romania means the primary country is `ro`. Logistics includes external
freight, delivery, forwarding and warehousing services. Selling trucks, logistics
software or equipment, and transporting one's own traded products do not alone qualify.
Ambiguous warehouse/logistics offerings remain uncertain.

For q2, software products and software development services are in scope;
`is_public` must be true and `employee_count` strictly greater than 1000.
A known contradiction is sufficient for rejection even if another field is missing.
Use supplied values, without replacing them with outside knowledge.

For q3, both primary cosmetic containers and protective shipping packaging count.
A supplier does not itself need a direct-to-consumer business model: that describes
the buyer. Explicit cosmetics/personal-care applications establish potential fit;
no claim is made about minimum order size, price or regulatory suitability.

## Baseline snapshot

| Query | Relevant | Not relevant | Insufficient information | Confirmed relevant / 10 |
|---|---:|---:|---:|---:|
| q1: Romanian logistics | 0 | 7 | 3 | 0.00 |
| q2: Public software, >1000 employees | 0 | 10 | 0 | 0.00 |
| q3: Cosmetics packaging suppliers | 6 | 3 | 1 | 0.60 |

These are provisional development results. Where cases are uncertain, the last
column is a lower bound, not a definitive precision estimate. The evaluator reports
new, unlabeled results as `unjudged`, never silently treating them as negatives.
Before comparing another model, judge its new results using the same rules.

## Observed failures

- q1: all top 10 score 2, often from `in` and `romania`, or `companies` and `in`.
  `Logistic` does not match `logistics`. Colaska (US) and Rantum Capital (Germany)
  are returned because no country filter is applied. CBRE serves the logistics
  real estate market, which does not establish logistics operations.
- q2: all top 10 have `is_public=false`. The ranker ignores this field and the
  employee constraint. Mentions of public clients or clients' employees can mislead it.
- q3: Flextribe supplies relevant packaging, but Rantum Capital and BrandSafway
  also rank highly due to common words and unrelated supply/consumer terminology.

Poșta Română, Globant, and BAOLILONG GLASS PACKAGING are additional relevant
examples outside the respective top 10. Their presence demonstrates missed results,
but three selected examples do not establish dataset-wide recall. The final
development comparison and local batch timings are reported in [WRITEUP.md](../WRITEUP.md).
The 12-query batch is a coverage check. Held-out relevance and dataset-wide recall
remain unmeasured.

Records are identified by a SHA-256 of the full normalized profile, not by name:
two different Rompetrol or Sesame HR records must not share a label accidentally.
The original dataset hash is checked before evaluation. For independent validation,
collect reviewed labels for a held-out query set.


## Additional profile inspection (2026-11-20)

All 26 profiles whose normalized primary country is Romania have proposed q1
judgments. Postal/parcel services and explicit cargo handling count as logistics;
property leasing, infrastructure access and ambiguous secondary offerings are
insufficient information. Product distribution alone is not logistics provision.
The prior reranker top tens for q2 and q3 have also been inspected. Software
includes development/engineering service providers, not only product publishers.
Packaging relevance means potential supply capability for cosmetics/personal-care
brands; no MOQ, price, or contract suitability is inferred. Existing labels are
preserved; added judgments carry proposed_by_assistant status and profile evidence.
These are development labels, not held-out accuracy or human review. Production
role rules never load the labels. Changes to the rubric need independent review.
