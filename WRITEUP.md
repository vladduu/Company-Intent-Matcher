# Intent Qualification — Writeup

## Approach

The first implemented step is loading and normalizing the dataset.
`address` and `primary_naics` can be dictionaries or strings representing dictionaries.
The loader tries JSON parsing for strings, then `ast.literal_eval` for Python
literal syntax. It does not use `eval`.

All records are kept in their original order, including exact duplicates.
Duplicate removal will be implemented separately.

Null values stay `None`; missing `address` or `primary_naics` fields become `None`.
Other fields are preserved as supplied, without filling in unknown values.
The original JSONL file is never modified.

Invalid records stop loading with a line number instead of being silently skipped.
This step does not validate every nested field or standardize country codes.

## Tradeoffs

To be documented after evaluating the initial approaches.

## Evaluation

No experiments have been run yet.

## Error Analysis

To be completed using concrete evaluation examples.

## Scaling

To be documented after implementing the initial pipeline.

## Failure Modes

To be documented as limitations are identified.
