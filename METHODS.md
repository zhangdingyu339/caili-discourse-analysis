# Methodological notes

## The source files are an incomplete research snapshot

The CSV has 363 rows, 142 distinct topic identifiers and one group. Fourteen rows
are marked as main posts; 349 are marked as replies. All 363 topic-title values
are missing. `contexts` contains uniform short strings and is not treated as full
context. The notebook's output-column names differ from the CSV and its save paths
are inconsistent. Collection quotas and dates in code are settings, not proof of
the realized sample. The JSON state records collection progress, not analysis data.

The full original corpus, Tieba input, original stopwords, frame lexicons and
analysis notebooks are absent from this snapshot. The report's K=10 model and
87.3% classification figure are not reproduced. This package instead uses up to
five exploratory NMF components and explicit new indicator lists. No paper result
is silently reused.

## Sampling and interpretation

Keyword selection includes housing and assets as well as bride price. Differences
in these terms may reflect query design, rather than platform culture or gender.
The crawler's title prefilter and thread/reply quotas can induce additional bias.
Posts from one group are not representative of Douban or Chinese public opinion.
The users' gender cannot be inferred from platform membership. Multiple replies
from a topic are not independent samples. Duplicate text removal does not remove
all quotations, reposts, author overlap or semantic near-duplicates.

NMF is unsupervised and its components are not automatically validated themes.
Normalized weights are algorithmic representations, not calibrated probabilities
of human-coded topics. Full-corpus topic fitting is acceptable for descriptive
exploration; it is separate from the training-only classifier pipeline. No
significance or platform differences are asserted from a synthetic demo.

Lexicon occurrence does not establish endorsement, aggression or latent framing.
The indicator denominators are Chinese character counts. Tokens and lexicon hits
have different definitions. Human annotation and sensitivity analysis would be
needed before stronger substantive claims.

## Publication boundaries

Raw texts, contexts, titles, timestamps at row level, group/topic identifiers,
topic URLs, collection state and authentication values are excluded. Even cleaned
verbatim text can remain searchable, so this package uses original synthetic
examples rather than anonymized source excerpts. The real-data audit contains
aggregate counts only. Original files are not modified or republished.

## Suggested future extensions

Recover the original analysis materials and authorized cross-platform data;
document collection queries and inclusion criteria; deduplicate quoted/near-
duplicate passages; evaluate group-disjoint robustness across multiple splits;
compare topic counts and tokenization choices; and validate frames using human
annotations. Keep these as future work, not completed accomplishments.
