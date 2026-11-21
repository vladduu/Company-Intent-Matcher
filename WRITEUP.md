# Intent Qualification

## 3.1 Approach

The system separates retrieval from qualification. A fast first pass finds promising profiles, a cross-encoder improves their ordering, and a final evidence check decides which profiles to return. This lets each stage address a different part of the request.

1. **Normalize the dataset.** Keep the first copy of each exact duplicate and preserve profile order. The supplied 477 records become 457 profiles. Normalize object fields such as `address` and `primary_naics` where the dataset stores serialized dictionaries. Preserve missing values and distinct profiles with the same company name.
2. **Extract supported constraints.** The English rule parser extracts the country or region, public status, employee count, USD revenue and founding year where it recognizes those conditions. It keeps the remaining activity text for search. Location checks use the country code in the primary address. For this project, Scandinavia means Denmark, Norway and Sweden. Regional groups are defined in `query_parser.py`.
3. **Filter and retrieve.** A known contradiction excludes a profile. Missing or invalid values in required fields produce an unknown verdict. Embed the remaining activity and compare it with normalized profile embeddings using cosine similarity. The default representation is the profile description. The system caches embeddings using the input text and encoder configuration, then reuses them across searches.
4. **Rerank the shortlist.** The local `cross-encoder/ms-marco-MiniLM-L6-v2` jointly reads the remaining activity and each shortlisted profile. It sees the description, offerings, business model and target markets. By default, it scores up to 100 profiles that pass structured constraints and up to 100 in the unknown group, if available. Reranker scores determine order within the candidate groups.
5. **Qualify on profile evidence.** Rules in `role_checks.py` and `intent_roles.py` check roles such as service provider, manufacturer and supplier, as well as query-specific requirements such as a stated platform or competition with banks. A cosmetics buyer and a packaging supplier play different roles. Likewise, a company using shipping internally does not automatically offer logistics to customers. Profiles with unknown required structured fields remain outside the qualified list. The final top limit is applied after qualification.

The parser and the role checks cover specific intent patterns and combinations. Their wording coverage is bounded. The pipeline can process an arbitrary input string, but support for its requirements depends on the parser and qualifiers. Evaluation labels and company names are outside the runtime rules.

## 3.2 Tradeoffs

- **Speed and cost.** Structured checks and cached embeddings narrow the work for the more expensive cross-encoder. The default path makes zero paid API calls per query and a batch reuses the model instances. There is still a local compute cost and a one-time model download. I did not benchmark a per-company LLM implementation, so the speedup against it is unknown.
- **Precision and coverage.** The evidence checks reduce intuitive false matches, such as a firm merely mentioning a target industry. Strict wording and required fields can also remove good matches. A conservative verdict makes those cases reviewable and leaves the qualified list shorter when evidence runs out.
- **Simplicity and flexibility.** Explicit constraints and profile excerpts make decisions traceable. They require maintenance when wording or sectors change. Description embeddings are compact and consistent, but the initial shortlist can miss a service that appears only in the offerings. The fuller representation is available for comparison.
- **Scope of evidence.** The system evaluates what the profiles support. It cannot verify a commercial relationship, supplier capacity, availability, or a fact missing from the provided data. For cosmetics packaging, direct-to-consumer describes the buyer and a match indicates potential supply fit.

### Development comparison

Both methods used description embeddings and returned up to 10 results on the same three development requests. The table counts results labeled relevant among the returned items.

| Request | Semantic only | Full pipeline |
|---|---:|---:|
| Logistics in Romania | 1 of 10 | 2 of 2 |
| Public software companies with more than 1,000 employees | 2 of 10 | 10 of 10 |
| Suppliers of cosmetics packaging | 8 of 10 | 10 of 10 |

The 64 labels were proposed with assistant help using profile evidence and are pending human review. The semantic results included one unjudged logistics profile, six unjudged software profiles and two unjudged packaging profiles. Three logistics results also had insufficient evidence for a decisive label. The counts describe this development comparison. Independent precision, dataset-wide recall and robustness on unseen requests require additional judgments.

### Results for the 12 provided queries

The numbers below are output counts from the default pipeline, with `--top 10`. They measure coverage of this run. Relevance outside the three development requests was not measured against reviewed labels.

| Request | Qualified results returned |
|---|---:|
| Logistics companies in Romania | 2 |
| Public software companies with more than 1,000 employees | 10 |
| Food and beverage manufacturers in France | 10 |
| Packaging suppliers for a direct-to-consumer cosmetics brand | 10 |
| US construction companies with revenue over USD 50 million | 10 |
| Pharmaceutical companies in Switzerland | 10 |
| European B2B SaaS companies providing HR solutions | 10 |
| Clean energy startups founded after 2018 with fewer than 200 employees | 0 |
| Fast-growing fintech companies competing with traditional banks in Europe | 0 |
| Ecommerce companies using Shopify or a similar platform | 0 |
| Renewable energy equipment manufacturers in Scandinavia | 10 |
| Manufacturers or suppliers of critical components for EV battery production | 10 |

On one local CPU batch run over 457 profiles with a populated embedding cache, model and index initialization took **7.5 seconds**, followed by **12.8 seconds** of total query processing across the 12 requests. These timings exclude first-time downloads and vary by hardware and candidate count. All 58 automated tests passed. The tests check code behavior, including filters and missing-data handling. Relevance was assessed separately in the development comparison above.

## 3.3 Error analysis

**Plausible matches the final pipeline missed.**

- **Lemartec** passed the US and revenue filters. Its description identifies it as a general contractor and its offerings include industrial and commercial construction. The final rule left it uncertain because the description did not match its construction execution pattern. This is a strong likely false negative on the supplied evidence. The rule should recognize contracting and explicit construction offerings together.
- **IguanaHR** describes a subscription HR software platform used by businesses. It reached the review list because the HR provider rule missed that phrasing. Review of this profile suggests a likely false negative. More provider patterns and a test covering this case would improve coverage.

**Why three qualified lists are empty.**

| Request | Candidate and missing evidence |
|---|---|
| Clean energy startups | **Norhybrid Renewables** passes the numeric filters with a 2020 founding year and 10 employees, and the profile supports the clean energy role. The startup rule demands explicit evidence of startup status. A young, small company can be a useful lead under a broader interpretation. |
| Fast-growing fintech competitors to banks | **European Pay** offers digital payments and collaborates with banks. The profile does not establish rapid growth or direct competition with traditional banks. The rule requires evidence of both. |
| Ecommerce using Shopify or similar platforms | **EasyKassa** offers ecommerce and payment technology. Its profile does not establish that it operates a store using Shopify or another supported platform. A company selling ecommerce technology plays a different role from a merchant using it. |

In these examples the pipeline abstains on the evidence it retrieved and checked. A relevant firm could still exist outside the shortlist or have an incomplete profile. All 12 requests execute, while the three empty lists remain a coverage gap against the goal of producing qualified companies for every query.

## 3.4 Scaling to 100,000 companies

The current implementation scans the profiles for structured checks and computes exact similarity over eligible vectors. Caching avoids re-encoding a company's text on every request. The cross-encoder work is bounded by the shortlist and run in batches. The Python and JSON representation of embeddings, full scan, and sorting of scored candidates would become bottlenecks as the dataset grows.

1. **Move work offline.** Normalize and validate profiles during ingestion, store structured fields in indexed columns, and encode new or changed profiles in batches. Version the index by model and text representation so old and new embeddings do not mix.
2. **Use an efficient retrieval path.** At 100,000 profiles, start with a compact float32 embedding matrix and vectorized exact similarity on the filtered subset. Use partial top-k selection to avoid sorting every score. If latency or memory requires an approximate nearest-neighbor index, measure recall on labeled queries and use metadata-aware retrieval or partitioning for selective filters.
3. **Keep qualification bounded.** Rerank only the shortlist, reuse models in a long-lived process, and choose shortlist sizes based on measured recall and latency. For millions of companies, consider partitioned vector search and batched reranker workers. Test p50 and p95 latency, memory usage and candidate recall before choosing an index or increasing the budget.

These changes are proposed. The 100,000-company and million-company configurations have not been benchmarked.

## 3.5 Failure modes and monitoring

| Failure mode | What to monitor |
|---|---|
| The parser misses a constraint or assigns it to the wrong field, such as treating an operating market as a headquarters location. | Extraction accuracy on reviewed queries, rates of unsupported wording, and the number of results violating sampled constraints. |
| A profile mentions an industry, customer, subsidiary or internal operation and the rule attributes the activity to the parent company. | Manually audited role precision and excerpts, grouped by intent and sector. |
| A stale or inaccurate profile reports a wrong employee count, listing status or product offering. | Missingness, data freshness, and contradictions across structured fields and text. |
| The shortlisting step misses relevant profiles because of description wording, truncation or a restrictive budget. | Candidate recall at the shortlist limit on a reviewed pool, judged misses and differences between description and full profile retrieval. |
| Rule changes or dataset drift increase the number of profiles marked uncertain or create apparently well-supported false positives. | Qualified coverage, empty-list rates, review outcomes, false positives and false negatives by query family, plus model startup and per-stage latency. |

The first improvement would be a manually reviewed, held-out set spanning all intent families, including candidates near the acceptance boundary and plausible misses below the shortlist. With that in place, I would test changes to the provider and startup rules, then compare them with selective model-based qualification on the difficult cases. That evaluation would let me measure the coverage gained and the additional errors introduced.
