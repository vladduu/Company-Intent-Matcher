# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

Dataset inspection, normalization, deduplication, and basic keyword search are available.
An optional rule parser, structured filters, and local embedding retrieval are
available. Optional API-based business-role qualification is available for a bounded hybrid shortlist; its quality still requires reviewed evaluation.

## Project structure

- `solution.py`: entry point for the solution.
- `data_loader.py`: dataset loading, exact deduplication, and field normalization.
- `keyword_search.py`: company text preparation and keyword ranking.
- `semantic_search.py`: local embeddings, profile cache, and semantic/hybrid retrieval.
- `query_parser.py`: limited English query rules.
- `filters.py`: three-state checks for structured conditions.
- `filtered_search.py`: filters followed by keyword ranking.
- `evaluate.py`: repeat the initial development evaluation.
- `evaluation/`: proposed labels, evidence, judgment rules, and baseline results.
- `WRITEUP.md`: approach, tradeoffs, evaluation, and limitations.
- `requirements.txt`: Python dependencies.
- `data/`: local dataset and data instructions.
- `scripts/inspect_dataset.py`: basic dataset inspection.

## Inspect the dataset

Place `companies.jsonl` in `data/`, then run from the project root:

```bash
python scripts/inspect_dataset.py
```

The script uses only the Python standard library.

This first version counts absent fields and null values as missing. It reports
types as stored, without parsing dictionary-like strings or cleaning the data.
It expects valid JSON objects on each non-empty line and loads the file into memory.

## Load and normalize the dataset

From the project root, run:

```bash
python solution.py
```

This currently loads the data, removes exact duplicate records, and prints the remaining count.
Without a query, it only loads the data. The loader converts `address`
and `primary_naics` into dictionaries and leaves the original file unchanged.
It uses only the Python standard library.

## Search companies

```bash
python solution.py --query "logistics" --top 10
python solution.py --query "software development" --top 5
```

`--top` must be positive and defaults to 10. Search uses the description,
core offerings, and business model. Results show the name, score, and matched words.
The score counts distinct query words found, ignoring case and punctuation.
Records with no matching words are excluded; ties keep dataset order.
This is a keyword baseline, not a probability or a qualification decision.
It does not understand synonyms, phrases, negation, location requirements, or
numeric constraints. Common words are not filtered out, so short keyword queries
are more useful than full sentences at this stage.

For `--method filters`, a small explicit word-variant map additionally normalizes
both the residual query and profile text: for example `logistic`/`logistics`,
`supplier`/`suppliers`, `cosmetic`/`cosmetics`, and `battery`/`batteries`.
See `WORD_VARIANTS` in `keyword_search.py` for the complete supported list.
Matched words display the normalized terms, which may differ from the original
spelling. Multiple variants of the same term contribute only one score point.
This is not general stemming or semantic understanding. The default `keyword`
method continues to use exact words for baseline comparisons.

## Try structured filters

```bash
python solution.py --method filters --query "Public software companies with more than 1,000 employees" --top 10
python solution.py --method filters --query "Logistics companies in Romania" --top 10
python evaluate.py --method keyword
python evaluate.py --method filters
python -m unittest discover -s tests -v
```

The default method remains `keyword` for reproducible baseline comparisons.
The `filters` method prints the parsed conditions and ranks passing candidates.
Candidates with unknown conditions appear separately, with at most `--top`
results per group. A known failed condition overrides an unknown condition.
Passing extracted filters does not establish full intent relevance.

Supported English patterns: a leading `public`, `publicly traded`, `private`,
or `privately held`; a trailing `in COUNTRY` (also `based in` / `located in`);
and `with more than/fewer than/at least/at most/exactly N employees` (also
`over`, `under`, `greater than`, `less than`). Integers may use thousands commas.
Country names and aliases are listed explicitly in `query_parser.py`; this is
not a comprehensive geography parser. Primary address defines location here.

Negation, alternatives, ranges and certain relationship phrases are deferred
without applying filters. Other residual text is retained for keyword search;
it is not guaranteed to be a correctly extracted activity. Unsupported constraints
can still be missed by these limited rules. See the extended filters below for revenue, founding year and region groups.
General synonyms and complex intent remain limited. No LLM calls or new dependencies
are required. The parsed query is kept in memory, not saved automatically.


## Semantic and hybrid search

Install dependencies with your normal Python installation:

```bash
python -m pip install -r requirements.txt
python solution.py --method semantic --query "Logistic companies in Romania" --top 10
python solution.py --method hybrid --query "Logistic companies in Romania" --top 10
python evaluate.py --method semantic
python evaluate.py --method hybrid
```

`semantic` embeds the complete query without hard filters. `hybrid` uses the
existing rule parser, applies its structured filters, and ranks candidates by
similarity to the residual activity text. Unknown filter conditions remain separate.
The default remains `keyword`. New candidates remain `unjudged` in evaluation
until their labels are reviewed; existing labels are not automatically changed.

The first semantic run downloads `sentence-transformers/all-MiniLM-L6-v2`.
Encoding runs locally on CPU, with no API key or per-query API calls. Network
access is needed for installation and initial model download. The model cache
and profile embeddings live under `.cache/semantic/`, already excluded from Git.
The profile cache key includes ordered input texts, encoder identity/revision,
library version and sequence limit. A changed key rebuilds all profile embeddings
in this first version. Corrupt cache data is rebuilt. Queries are encoded per call.

Profiles contain labeled core offerings, description, business model and target
markets. Core offerings come first; long profiles can be truncated at the model's
sequence limit (normally 256 word pieces). This can lose important evidence.
Scores are cosine similarity, not probabilities. No relevance threshold has been
calibrated: the method returns up to `--top` candidates, even when all are weak.
Passing filters and high similarity do not confirm the requested business role.
The parser still has its documented limitations. Supported revenue, year and regional constraints are handled explicitly by the
parser and filters, not by the embeddings.

Model documentation: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
Semantic search documentation: https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html


## Compare profile representations

The default `full` profile preserves the original input fields. `description`
uses only the description; missing descriptions are excluded from activity search.
Each representation has a separate embedding cache. This is an experiment, not
an assumed accuracy improvement. Run the same queries and review their profiles:

```powershell
python evaluate.py --method hybrid --profile full --output outputs/hybrid-full.json
python evaluate.py --method hybrid --profile description --output outputs/hybrid-description.json
```

Reports include company profiles, IDs, scores, existing proposed labels and
unknown/rejected candidates. They never overwrite development labels. Unjudged
results are not negatives. Review new results manually before claiming precision.

## Qualify a shortlist (optional API calls)

Set these environment variables in your PowerShell terminal (do not commit keys):

```powershell
$env:OPENAI_API_KEY="YOUR_API_KEY"
$env:QUALIFICATION_MODEL="YOUR_STRUCTURED_OUTPUT_MODEL"
python solution.py --method hybrid --profile description --qualify --candidates 30 --query "Logistics companies in Romania" --top 10
python evaluate.py --method hybrid --profile description --qualify --candidates 30 --output outputs/qualified-description.json
```

Choose an OpenAI model available to your API account that supports structured
outputs. API usage requires separate API access/billing. This option sends the
query and full profiles of up to 30 passing candidates to OpenAI, one at a time;
it does not send the entire dataset. No additional Python dependency is required.
Without `--qualify`, retrieval remains local after the model download.

Qualification checks the original query, including constraints unsupported by the
parser. It returns relevant, not_relevant or insufficient_information with a reason
and verbatim profile evidence. Evidence strings are checked against profile values;
this guards against invented quotes, but does not prove the reasoning is correct.
Missing/invalid evidence cannot produce an accepted result. Unknown structured
filter candidates remain separate and are not sent for qualification. Results keep
semantic order within the accepted group; fewer than --top results is valid.

Verdicts are cached under `.cache/qualification` by query, full profile, model,
prompt and schema. Repeated requests reuse successful verdicts. API/network failures
stop the run with an error; prior successful verdicts remain cached. Use a versioned
model name when available for reproducibility. Manual deletion of this cache forces
fresh judgments. No automatic retries, concurrent API calls or recall guarantee
are implemented yet. Relevant companies outside the shortlist cannot be recovered.

API reference: https://developers.openai.com/api/reference/resources/responses/methods/create


## Local reranking (no API key)

```powershell
python solution.py --method rerank --profile description --query "Logistics companies in Romania" --top 10
python evaluate.py --method rerank --profile description --output outputs/rerank-description.json
```

`rerank` applies the existing structured filters, retrieves up to `--candidates`
profiles per pass/unknown group (default 100), then scores query/profile pairs
locally with `cross-encoder/ms-marco-MiniLM-L6-v2`. It reranks before taking the
final top results. Unknown filter candidates remain separate. The residual
activity is used after supported hard constraints are checked. The reranker reads
the description first, followed by offerings, business model and target markets;
`--profile` controls the initial embedding retrieval only. Empty activity preserves
filter-only ordering. Profiles with no usable text cannot be ranked for activity.

The first run downloads another model (about 90 MB weights) into `.cache/reranker`.
It runs on CPU with the existing sentence-transformers dependency. No Gemini,
OpenAI account, key or API calls are involved in this method. Original retrieval
scores are retained in JSON as `retrieval_score`; the final `score` is a raw
reranker logit, which can be negative and is not a probability. Scores cannot be
compared to embedding cosine scores. No arbitrary acceptance threshold is used.
This improves the ranking architecture but is not a verified qualification verdict.

For this small dataset, `--candidates 457` can test shortlist recall by reranking
all text-bearing profiles that survive filters. That costs more CPU time. At
scale, keep a bounded shortlist and measure recall against reviewed judgments.
Model reference: https://sbert.net/docs/cross_encoder/pretrained_models.html


### Evidence-based local selection

`rerank` now checks supported business roles after reranking the whole shortlist,
before taking `--top`. It may return fewer results; rejected or uncertain candidates
are never added just to fill the list. `--rank-only` restores the ranking baseline.
`logistic` and `logistics` are canonicalized by the structured parser, so these
variants share retrieval and reranking behavior.

The local role rules in `role_checks.py` currently cover simple logistics requests,
software (including software engineering/services providers), and the development
query asking for potential cosmetics-packaging suppliers. They require profile
evidence, preserve unknown structured conditions, and report the source of each
judgment. Infrastructure/facility leasing and contradictory offering lists are
uncertain. Packaging capability is not a guarantee of price, MOQ, certification,
or suitability for a particular customer. Unsupported residual intent is returned
for review rather than silently qualified. These bounded rules do NOT solve all
12 challenge queries or arbitrary English; they prioritize precision on supported
roles at a possible recall cost. No company names, IDs or evaluation labels enter
the production rules. No score threshold has been selected from this dataset.

```powershell
python evaluate.py --method rerank --profile description --output outputs/rerank-qualified.json
python evaluate.py --method rerank --profile description --rank-only --output outputs/rerank-baseline.json
```

Development labels now include assistant inspection of all 26 Romanian profiles
and the previous top-ten software/packaging results. They remain proposals, not
human-validated ground truth. The reports retain all uncertain shortlist candidates
in `review_candidates` and rejected candidates separately. Relevant@10 penalizes
returning fewer than ten even when the dataset has fewer matches; precision among
returned results is also printed when all returned labels are decisive. Neither
metric establishes generalization on these development queries.


## Extended structured filters

Revenue is interpreted in USD, matching the dataset. Examples accepted include
`revenue over $50 million`, `annual revenue at least USD 1.5 billion`, `$50m`,
`500 thousand dollars`, and `50,000,000 USD`. Unqualified amounts also mean USD.
Other currencies are left in the residual with a warning; no exchange conversion
is attempted. Malformed numbers are not partially accepted.

`founded` and `established` support `after` (>), `before` (<), `since` (>=) and
`in` (==), followed by a four-digit year. Employee comparisons may follow `with`
or `and`, allowing year/revenue/employee constraints to combine. Missing or invalid
values produce unknown; a known failed condition still dominates unknown. Year
values must be integral, in 1..9999; numeric strings are not silently coerced.

`in Europe`, `in Scandinavia` and `in the Nordic countries` produce country-code
membership filters. They use the primary address, not countries served. Scandinavia
means Denmark, Norway and Sweden; Nordic countries additionally include Finland and
Iceland. Europe is a declared project grouping (see REGIONS in query_parser.py),
including the UK, Switzerland, Russia, Turkey and Cyprus; it is not EU membership.
The available country code cannot resolve continental parts of countries. Territories
are not automatically included. These scope choices should be reviewed for production.

```powershell
python solution.py --method filters --query 'Construction companies in the United States with revenue over $50 million' --top 10
python solution.py --method filters --query "Clean energy startups founded after 2018 with fewer than 200 employees" --top 10
```

In PowerShell use single quotes around queries containing `$` to avoid variable
expansion, for example:

```powershell
python solution.py --method filters --query 'Construction companies in the United States with revenue over $50 million' --top 10
```

These filters check the structured conditions only. Local role qualification still
covers the previously documented roles; construction, clean energy and other new
roles are not qualified automatically by this increment. `--method rerank --rank-only`
can inspect ranked candidates without claiming qualification. Negation, ranges and
customer/operating-location scope continue to be deferred with warnings.
