# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

Dataset inspection, normalization, deduplication, and basic keyword search are available.
An optional rule parser, structured filters, and local embedding retrieval are
available. Full business-role qualification is not implemented yet.

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
can still be missed by these limited rules. Revenue, founding year, region groups,
synonyms and complex intent remain future work. No LLM calls or new dependencies
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
The parser still has its documented limitations. Revenue, year and regional
constraints are not magically handled by adding embeddings.

Model documentation: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
Semantic search documentation: https://www.sbert.net/examples/sentence_transformer/applications/semantic-search/README.html
