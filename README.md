# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

Dataset inspection, loading, and normalization are available. The qualification pipeline is not implemented yet.

## Project structure

- `solution.py`: entry point for the solution.
- `data_loader.py`: dataset loading, exact deduplication, and field normalization.
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
It does not perform matching yet. The loader converts `address`
and `primary_naics` into dictionaries and leaves the original file unchanged.
It uses only the Python standard library.
