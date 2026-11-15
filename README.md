# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

Dataset inspection, normalization, deduplication, and basic keyword search are available.
Semantic matching and constraint qualification are not implemented yet.

## Project structure

- `solution.py`: entry point for the solution.
- `data_loader.py`: dataset loading, exact deduplication, and field normalization.
- `keyword_search.py`: company text preparation and keyword ranking.
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
