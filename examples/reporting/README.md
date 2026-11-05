# Reporting tool — fictional sample

This is the existing Python generator, distributed without its real research or sales records. All three sample records and numbers are fictional test fixtures; do not contact them. No outreach or network requests are performed. The date field is a fixture, not research evidence.

Requires Python3.12 and openpyxl.

    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    .venv/bin/python lead_generator.py validate
    .venv/bin/python lead_generator.py generate --output tracker.xlsx

Edit sales fields in tracker.xlsx, retain Lead IDs, then regenerate the same output to preserve those fields. Removed tracked IDs stop the refresh. Open Excel/LibreOffice to recalculate dashboard formulas.
