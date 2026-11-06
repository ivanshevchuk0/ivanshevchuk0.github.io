# Campaign Evidence — offline advertising export QA

Personal technical demonstration by Ivan Shevchuk. All included campaign data is fictional. No client accounts, ad budgets, credentials, tracking tags or external AI service are used. This is working reporting software, not evidence of campaign-management experience.

## Run

Python 3.10+; standard library only. From this folder:

```bash
python3 campaign_report.py fictional-campaigns.csv --output example-output --label "FICTIONAL DEMO DATA"
python3 -m unittest discover -s . -v
```

Open [the sample HTML report](example-output/report.html). It works offline. Outputs also include structured report.json and an ai-review-brief.json for a future, separately approved human-reviewed AI workflow. **No AI analysis is currently generated.**

## Input contract

UTF-8 or UTF-8-BOM CSV, exactly these headers:

```text
date,source,campaign_id,campaign,currency,impressions,clicks,spend,conversions,conversion_value
```

- This is a canonical normalized schema, NOT a native Google/Meta/TikTok export importer. Export column mapping is a separate onboarding step. Source is google, meta or tiktok; these labels do not imply an API integration.
- One row per date/source/campaign_id/currency. Duplicate daily keys are rejected, not silently summed. Segmented exports need explicit upstream aggregation first.
- Dates must be YYYY-MM-DD; counts whole and nonnegative; spend/conversions/value finite and nonnegative. Fractional attributed conversions are allowed. Refund/negative adjustments are outside v1 scope.
- Currency is a three-letter uppercase code; syntax is checked, not membership of an ISO currency registry. No FX conversion.
- Blank conversion_value means unknown, not zero. Missing any value in a campaign suppresses its value total and ROAS.
- Preserve string IDs. Rename campaign names and IDs to non-sensitive aliases before any external sharing. Extra CSV columns are rejected, but that is not a comprehensive personal-data detector.
- Confirm that conversion columns use a consistent definition and attribution window for each campaign. Use a single account timezone per source. The tool does not verify these assertions.

## What works

Decimal-based sums; weighted CTR=clicks/impressions, CPC=spend/clicks, cost per platform conversion=spend/conversions, platform ROAS=value/spend; safe zero denominators; campaign/source/currency isolation; duplicate/invalid-input rejection; HTML escaping; responsive standalone report; explicit limitations; deterministic review flags.

Sample check: fictional Google campaign totals 4,000 impressions, 100 clicks, PLN 200 spend, 5 platform conversions; CTR 2.50%, CPC PLN 2.00, CPA PLN 40.00. No confirmed sales or revenue is inferred. Its conversion value is missing, so ROAS is unavailable.

## Boundaries

Platform conversions can overlap across networks; do not sum them into unique sales. A clean export is not proof of working tracking, consent compliance, profit or cash receipts. Flags ask questions; they do not recommend budget changes. No dashboard authentication is needed for fictional data; real client reports must be shared privately, never on GitHub Pages.

Native export adapters, Google Ads OAuth/developer access, Meta Marketing API permissions, scheduled refreshes, CRM matching, consent implementation, and AI-provider integration are NOT implemented. Add them only for a funded scope with client authorization. No always-on monitoring or service-level promise.

## Validation

12 unittest cases cover weighted metrics, currency separation, missing values, zero denominators, duplicate keys, fractional attribution, invalid inputs, extra fields, HTML injection, and real CLI success/failure. Desktop 1440px and mobile 390px report checked in Chromium on 2026-11-06; no horizontal overflow observed.

## Data and ownership

Only original demonstration code and fictional data belong in this public example. Prospect lists, research, private CVs, identity files and client exports stay outside this directory. No open-source license or client IP transfer has been added.
