# Intent Qualification — Writeup

## Approach

The first implemented step is loading and normalizing the dataset.
`address` and `primary_naics` can be dictionaries or strings representing dictionaries.
The loader tries JSON parsing for strings, then `ast.literal_eval` for Python
literal syntax. It does not use `eval`.

Exact duplicates are detected before normalization by comparing all original
fields with sorted dictionary keys. The first occurrence is kept, and companies
are not merged by name. Original record order is preserved.

Null values stay `None`; missing `address` or `primary_naics` fields become `None`.
Other fields are preserved as supplied, without filling in unknown values.
The original JSONL file is never modified.

Invalid records stop loading with a line number instead of being silently skipped.
This step does not validate every nested field or standardize country codes.

## Tradeoffs

An optional `filters` method applies a bounded English rule parser, followed by
three-state structured checks and keyword ranking of residual text. Supported
fields are primary country (including configured region groups), public status,
employee count, USD revenue, and founding year. Filters apply
before top-result truncation. Missing or invalid field values are unknown;
known contradictions exclude a candidate even when another condition is unknown.
Unknown candidates remain in a separate result group. Passing these checks is
not a full relevance decision. The rule-based methods require no external models or API calls.

The parser is intentionally limited to documented patterns. It defers some
negated/relational requests and retains residual text, but cannot guarantee that
every unsupported condition is detected. Incorrect extraction remains a risk.

The keyword baseline combines description, core offerings, and business model.
It splits text into lowercase alphanumeric words and scores a company by the
number of distinct query words present. Repetition does not increase the score.
Only positive scores are returned; ties preserve dataset order.
This provides a transparent baseline without external dependencies, but cannot
distinguish an offered service from a passing mention of an industry.

## Evaluation

A first development evaluation covers three exact challenge examples and their
top 10 keyword results, plus one additional relevant candidate per query.
The 33 labels are assistant-proposed, based on supplied profile evidence, and
pending human review. They are not independent ground truth or a held-out test.

Run `python evaluate.py`. See `evaluation/README.md` for judgment rules and
`evaluation/development_cases.json` for evidence, reasons, and record identifiers.
Confirmed relevant results in the top 10 are 0 for Romanian logistics, 0 for
public software companies with >1000 employees, and 6 for cosmetics packaging.
There are respectively 3, 0, and 1 uncertain judgments; confirmed-relevant@10
is a lower bound where uncertainty remains. Dataset-wide recall is not measured.
The keyword algorithm was left unchanged to preserve this baseline.

## Error Analysis

Initially, filters alone returned no candidates for q1 because `logistic` did
not match `logistics`, even though 26 profiles passed the country check.
The filtered method now applies a small explicit variant map to both query and
profile words. It returns 10 candidates for q1, including Poșta Română (labeled
relevant), but also Rompetrol and CBRE (labeled not relevant). Five results are
unjudged and two uncertain. This fixes the lexical mismatch, not role qualification.
The map also covers selected singular/plural pairs such as supplier/suppliers
and battery/batteries. It does not remove suffixes indiscriminately, recognize
arbitrary synonyms, or double-count variants of one term. The keyword baseline
retains exact matching. In q3, Minh Trang Packaging is a new unjudged result;
six results retain relevant labels, two not-relevant and one uncertain.
For q2, 36 profiles pass public/employee checks; every returned candidate meets
these structured conditions, but its software role still needs review. Of the
top 10, only Globant has an existing relevant judgment; the other nine are
unjudged, so a quality improvement cannot yet be quantified from those labels.
The original keyword baseline and evaluation labels remain unchanged.

The exact query `Logistic companies in Romania` also exposes a word-inflection
failure (`logistic` versus `logistics`) and matches on common words such as `in`.
For the public software query, all top 10 profiles have `is_public=false`.
For cosmetics packaging, Rantum Capital and BrandSafway appear despite unrelated
business roles. These results motivate explicit constraints and role qualification.

In a manual check of `logistics`, CBRE Romania is returned because its profile
mentions logistics as a client sector/property type. The description identifies
it as a commercial real estate service provider. Keyword overlap alone therefore
does not establish that the company offers logistics services.

## Scaling

To be documented after implementing the initial pipeline.

## Failure Modes

Keyword matching does not handle synonyms, word inflections, phrase meaning,
negation, or structured constraints such as country and employee count.
Common query words are not removed. Single-word queries give every matching
company the same score, so their order is not a semantic relevance ranking.
No keyword matches means no lexical overlap, not proof that no company qualifies.


## Local embedding retrieval

Added `semantic` (full-query similarity baseline) and `hybrid` (existing hard
filters plus residual-text similarity). The local all-MiniLM-L6-v2 encoder produces
normalized vectors; their dot product is cosine similarity. Core offerings precede
description, business model and target markets in profile text. Model truncation
may omit later evidence. An embedding score is not a qualification verdict.

The index is cached by ordered texts and encoder configuration/revision. It is
reused across queries; changing its identity rebuilds the full index. The first
implementation uses Python vectors and a linear scan, appropriate to 457 profiles.
At 100,000 profiles, use compact float32 arrays, vectorized scoring or an ANN index,
filter-aware retrieval, and per-record incremental embedding updates. Benchmark
retrieval recall before adopting approximate search. Cold model startup and index
creation must be measured separately from warm query latency.

Automated tests use an injected deterministic test encoder to verify cache reuse,
cache invalidation, corruption recovery, ranking and filter/unknown separation.
Those tests verify software behavior, not model quality. Semantic accuracy must be
measured with the real model and reviewed labels; no automatic relabeling is done.


Validation status for this implementation: 22 automated tests passed, including
six tests using a deterministic fake encoder. The real embedding model has not
been run here. Dependency installation into the user Python directory failed
with Windows access denied; a temporary-target installation stopped reporting
progress and was interrupted. Therefore no semantic quality or latency results
are claimed yet. Complete installation and run both semantic and hybrid evaluation
before drawing conclusions or treating this as a validated submission.


## Profile ablation and selective qualification

Added explicit full/description representation selection with separate embedding
cache identities. Full remains the baseline; description-only can lose offering
evidence and excludes profiles without descriptions. Compare both on identical
queries before selecting a default. The supplied real-model rankings exposed
retailers and companies using logistics internally among logistics results.

Optional qualification sends only the passing hybrid shortlist to an API model,
using the original query and full profiles. Its three-state verdict, explanation
and exact evidence excerpts distinguish business roles. Excerpts must occur in
the profile; that check cannot validate the interpretation or source accuracy.
Labels in the development set remain independent from generated verdicts.
Reports expose profiles for human review, decisive-label coverage and unjudged
counts. Current labels remain assistant-proposed, not verified ground truth.

Tradeoffs: one request per uncached candidate is simple but sequential and may be
slow. The shortlist caps cost but limits recall. Cache identity covers query,
profile, prompt, schema and model name; mutable model aliases can still change.
Unsupported filters may survive retrieval, so the qualifier must inspect all
constraints. Missing evidence is unknown rather than assumed false. Monitor
acceptance/unknown rates, retrieval recall on reviewed samples, invalid evidence,
API failures, latency and cache hit rates before production. At scale, batch or
bound concurrency for shortlist calls and use indexed candidate retrieval.

Validation of this increment: 26 offline tests pass, including evidence rejection,
qualification cache invalidation, unknown separation and description-mode isolation.
Live API qualification has not been tested with credentials. Real-model evaluation
in this tool environment was blocked by missing socksio for its configured proxy;
no measured accuracy improvement is claimed. The user's earlier local runs worked.


## Local reranking alternative

The `rerank` method requires no paid API: bounded hybrid retrieval feeds a local
MS MARCO MiniLM cross-encoder. Unlike independently computed embeddings, it scores
each query/profile pair jointly. Description-first text prioritizes main activity;
512-token truncation can still omit evidence. It is a general passage relevance
model, not a model trained on these company labels. Missing facts and complex
business roles remain potential failures. No uncalibrated score is presented as a
probability or definitive verdict. Unknown filter groups remain separate.

Default shortlist size is 100 per group. This covers all 26 Romanian candidates
and all 36 candidates passing the public/employee filters in the current dataset.
Unconstrained queries still depend on retrieval recall. At scale, use indexed
retrieval, measure recall, and bound reranking cost. API qualification remains an
optional separate experiment; it is not used by the local rerank method.

Thirty automated tests pass, including reranking order, preservation of unknown
filter status, invalid score rejection and filter-only queries. These software
tests use deterministic doubles and do not establish model accuracy.


Real-model validation of local reranking completed on the 457 normalized profiles
with description retrieval and 100 candidates. The report is saved locally at
outputs/rerank-description.json. For q1, Brasov Industrial Portfolio ranked first
and Posta Romana tenth; Dacia and Sincron HR dropped out of the top ten. CBRE
Romania remains a known negative, so the role distinction is not solved. For q2,
Globant ranked first and EPAM second; Bachem and Siegfried left the top ten. For
q3, five returned companies have proposed relevant labels and five are unjudged.
The proposed-label relevant@10 lower bounds are 0.10, 0.10 and 0.50 respectively;
these are not reviewed precision estimates or proof of general accuracy gains.
The test process used a temporary workspace copy of socksio for its SOCKS proxy;
no Python environment or system settings were modified.


## Conservative local role selection (2026-11-20)

Reranking alone still put property and equipment providers among logistics firms.
The local pipeline now checks explicit role evidence across the ranked shortlist
before limiting the accepted list. It does not fill vacant top-ten slots. Simple
logistics activity, software provision (including engineering services), and the
cosmetics-packaging development intent have bounded rules. Description evidence is
required; ambiguous infrastructure/facility leasing and secondary service claims
are separated for review. Unknown structured conditions cannot become accepted.
Extra unsupported residual constraints cannot be silently discarded by these
rules: they abstain. They are not a general solution to the twelve challenge
queries; new role families and independent evaluation remain necessary.

Logistic/logistics normalize identically in the parser. Runtime rules contain no
company names or dataset IDs and never load the development labels. Evaluation
labels were separately extended through assistant profile inspection: all 26
Romanian profiles have proposed judgments (2 relevant, 9 insufficient, 15 negative),
as do the prior software and packaging top tens. Human review remains outstanding.
The definition includes explicit external postal/parcel/cargo-handling services;
software includes development services; packaging means potential supply, not a
verified contract fit. Altering these definitions may alter the judgments.

Real-model evaluation with description retrieval and 100 candidates now returns
Posta Romana and Portul Constanta for q1; q2 returns ten proposed-relevant software
providers beginning Globant, EPAM and Tata Consultancy Services; q3 returns ten
proposed-relevant packaging suppliers. The proposed-label relevant@10 values are
0.20, 1.00 and 1.00. These are DEVELOPMENT results with assistant-proposed labels,
not independent accuracy. Some score increases reflect labeling previously
unjudged candidates, not better ranking. Conservative rules can lose true matches,
especially unseen phrasing and secondary activities. No minimum logit cutoff is
claimed to be calibrated. `--rank-only` retains the original ranking experiment.

Validation: 39 tests passed; real-model evaluation completed for all three queries;
a separate real-model check confirmed identical accepted company lists AND scores
for Logistic and Logistics. The review report is outputs/rerank-qualified.json.


## Extended filters: revenue, founding year and geographic groups

Added explicit USD revenue comparisons with magnitude suffixes, four-digit founding
year comparisons, and country-set membership for Europe/Scandinavia/Nordic countries.
The parser retains unsupported currency/constraint wording instead of inventing
values. No conversions or missing-value imputations are made. Boolean values and
nonfinite numeric data are unknown; invalid filter definitions fail fast. Conditions
combine with AND, and a known failure dominates unknown. Year/employee boundaries
are strict or inclusive according to the operator, with dedicated regression tests.

Region membership is a documented project convention: primary address only, Europe
includes transcontinental Russia/Turkey and Cyprus, and Scandinavia excludes Finland
and Iceland. It is not an EU filter or a guarantee about a company's operating reach.
Unsupported country names and territories remain a limitation.

On the real dataset, US + revenue >50m yields 49 passes, 6 unknown and 402 failures;
year >2018 + employees <200 yields 82 passes, 141 unknown and 234 failures; Europe
matches 286 primary addresses and Scandinavia 64. These are structured-filter counts,
not counts of relevant construction, clean-energy, HR SaaS or equipment companies.
Role coverage is unchanged. This distinction prevents reporting numeric/location
filter success as intent qualification. Forty-eight automated tests pass.

Real-model regression after the extension preserved the three development result
lists: 2 logistics results, 10 software results and 10 packaging results. The
report is outputs/extended-filter-regression.json; labels are still proposed.
