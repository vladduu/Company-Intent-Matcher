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

The keyword baseline combines description, core offerings, and business model.
It splits text into lowercase alphanumeric words and scores a company by the
number of distinct query words present. Repetition does not increase the score.
Only positive scores are returned; ties preserve dataset order.
This provides a transparent baseline without external dependencies, but cannot
distinguish an offered service from a passing mention of an industry.

## Evaluation

Retrieval quality has not yet been measured on a labeled evaluation set.

## Error Analysis

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
