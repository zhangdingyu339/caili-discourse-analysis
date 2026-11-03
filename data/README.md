# Public data: synthetic examples only

`synthetic_demo.csv` contains original, fabricated Chinese sentences to demonstrate
the software. None are quotations, paraphrases, anonymized copies or extracted
snippets from the supplied social-media corpus. Synthetic rows cannot establish
real platform or gender differences.

For private analysis, place your authorized CSV inside `private/`. It must contain
`text` and either `topic_id` or `thread_id`. An optional `platform` column defaults
to `douban` when absent. To compare platforms, concatenate both platforms into one
CSV with explicit labels and source thread identifiers; do not invent missing data.
Thread IDs must refer to the original topic across all its comments/pages.

The supplied source CSV has 11 fields, including original topic links and text.
Only text, platform and thread ID are consumed; contexts, titles, query fields,
links and state files are not exported. No claim of complete anonymization is made.
