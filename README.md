# Company Intent Matcher

A project for the Veridion Intent Qualification challenge: ranking and qualifying companies against a user's request.

## Status

The dataset inspection script is available. The qualification pipeline is not implemented yet.

## Project structure

- `solution.py`: entry point for the solution.
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
