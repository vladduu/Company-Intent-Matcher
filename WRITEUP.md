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
fields are primary country, public status, and employee count. Filters apply
before top-result truncation. Missing or invalid field values are unknown;
known contradictions exclude a candidate even when another condition is unknown.
Unknown candidates remain in a separate result group. Passing these checks is
not a full relevance decision. No external models or API calls are used yet.

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
