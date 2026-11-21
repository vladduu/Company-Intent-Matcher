# Company Intent Matcher

A company search and qualification system for the Veridion Intent Qualification challenge. The default mode runs locally and ranks companies whose profiles support the requested activity and structured constraints.

## Setup

Use Python 3.11 and place the supplied dataset at `data/companies.jsonl`. The dataset is distributed with the challenge and excluded from Git. From the repository root, run:

```powershell
python -m pip install -r requirements.txt
```

The first default search needs internet access to download the two Hugging Face models. Later runs can reuse the local model and embedding cache. The default search requires no API key.

## Run a search

```powershell
python solution.py --query 'Logistics companies in Romania'
python solution.py --query 'Construction companies in the United States with revenue over $50 million' --top 5 --details
```

Use single quotes in PowerShell when a query contains a dollar amount. The default method is `rerank`, with description-based embeddings. `--top` caps the number of displayed results and defaults to 10. The regular view shows accepted companies and their qualification reasons, plus a count of shortlisted candidates needing review. Use `--details` to see parsed conditions, ranking scores, evidence excerpts and shortlisted candidates needing review. An empty qualified list means the search found insufficient support to accept a candidate under its current rules.

Use `--data path/to/companies.jsonl` to select a different input file with the same schema.

## Run all 12 example requests

```powershell
python solution.py --queries queries.json
python solution.py --queries queries.json --output outputs/results.json
```

The batch loads the dataset and models once. Passing `--output` creates a JSON report with the search configuration, per-query timings, results and supporting evidence. Omit it for terminal output only. You can supply your own query list using the same `id` and `text` fields as [queries.json](queries.json).

## Review or compare methods

| Method | What it does |
|---|---|
| `keyword` | Ranks by distinct matching words. |
| `filters` | Applies structured filters and ranks by keyword overlap. |
| `semantic` | Ranks the full query by embedding similarity. |
| `hybrid` | Applies structured filters and ranks the remaining activity by embedding similarity. |
| `rerank` | Reorders the hybrid shortlist with a local cross-encoder and qualifies results using role evidence. |

`--method rerank --rank-only` skips the final local qualification step for comparison. Set `--profile full` to use additional profile fields during embedding retrieval. `--candidates` sets the shortlist limit per filter group and defaults to 100. Model scores are ranking signals and have no probability interpretation.

The three-query development comparison uses the same description representation for both methods:

```powershell
python evaluate.py --method semantic --profile description
python evaluate.py --method rerank --profile description
python -m unittest discover -s tests -v
```

Development labels are provisional and partly cover the returned profiles. The [writeup](WRITEUP.md) explains the measured comparison, all 12 batch outcomes, the empty results, and the limits of the evaluation.

The optional `--method hybrid --qualify` experiment sends the query and shortlisted company profiles to OpenAI for qualification. It uses `OPENAI_API_KEY` and `QUALIFICATION_MODEL` and may incur API charges. The results in the writeup use the local default pipeline.

## Code map

| File | Responsibility |
|---|---|
| `solution.py`, `pipeline.py` | Single and batch search, pipeline setup and reporting |
| `data_loader.py`, `scripts/inspect_dataset.py` | Dataset normalization, deduplication and inspection |
| `query_parser.py`, `filters.py` | Structured constraint extraction and checks |
| `keyword_search.py`, `filtered_search.py`, `semantic_search.py`, `reranker.py` | Retrieval, baselines and reranking |
| `role_checks.py`, `intent_roles.py` | Business-role checks and evidence |
| `evaluate.py`, `evaluation/`, `tests/` | Development comparison, cases and automated tests |
