# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

Dataset inspection, normalization, deduplication, and basic keyword search are available.
An optional rule parser and structured filters are available. Semantic matching
and full intent qualification are not implemented yet.

## Project structure

- `solution.py`: entry point for the solution.
- `data_loader.py`: dataset loading, exact deduplication, and field normalization.
- `keyword_search.py`: company text preparation and keyword ranking.
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
