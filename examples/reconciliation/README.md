# CSV export reconciliation preflight

A small AI-assisted personal demonstration for checking whether two exports can be joined safely. Uses only fictional fixtures. Not client work, an advertising integration, or a production analytics system. No third-party project names or source are included.

## Run (Python 3.10+, standard library only)

    python3 reconcile.py left.csv right.csv --left-key id --right-key lead_id
    python3 -m unittest discover -s . -p "test_*.py" -v

The example reports two records per file, one matched key and one unmatched key on each side. It does not alter the inputs or contact any API. Invalid headers, missing/empty/duplicate keys, ragged CSV rows, unreadable input or excessive rows return a JSON error and exit 2. Successful runs exit 0. Keys are trimmed of surrounding whitespace; leading zeros remain significant. Output contains counts, not raw record identifiers.

## Limits

This preflight assumes one record per key on each side. Real advertising and CRM data often have many-to-one relationships and changing event history; this tool deliberately rejects duplicate keys rather than pretending those relationships are resolved. Key overlap alone does not prove correct attribution, correct financial metrics, consent, API access or payment eligibility. UTF-8 CSV only, comma-separated. Confirm the schema and expected relationship before applying it to real data.

## Paid service path

A possible paid first task is to assess an authorized, redacted export pair and document the join keys, duplicates and unmatched-record policy, then separately agree implementation and acceptance tests. Existing service pricing is unchanged; scope, price, timing, data/tool rules, ownership terms and protected funding require separate approval. No client data is needed for this demonstration.

Validation performed: 10 automated tests passed, including duplicate rejection, invalid shapes, leading zeros, Unicode/BOM input, unchanged source files and CLI failure behaviour. Owner review is still separate from automated verification.
