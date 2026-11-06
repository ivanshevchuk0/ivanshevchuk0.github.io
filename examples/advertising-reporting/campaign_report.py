#!/usr/bin/env python3
"""Offline advertising export QA. No credentials, network or campaign writes."""
import argparse, csv, html, json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

REQUIRED = {'date','source','campaign_id','campaign','currency','impressions','clicks','spend','conversions','conversion_value'}
NUMERIC = ('impressions','clicks','spend','conversions','conversion_value')

def number(value, field, line):
    try:
        n = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f'Line {line}: invalid {field}') from exc
    if not n.is_finite() or n < 0:
        raise ValueError(f'Line {line}: {field} must be finite and non-negative')
    if field in ('clicks','impressions') and n != n.to_integral_value():
        raise ValueError(f'Line {line}: {field} must be an integer')
    return n

def load_rows(path):
    rows, seen = [], set()
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)) or set(headers) != REQUIRED:
            raise ValueError('Use exactly the documented CSV headers; unexpected fields may contain private data')
        for line, row in enumerate(reader, 2):
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f'Line {line}: ragged CSV record')
            row = {k:v.strip() for k,v in row.items()}
            try:
                parsed_date = date.fromisoformat(row['date'])
                if parsed_date.isoformat() != row['date']:
                    raise ValueError('Noncanonical ISO date')
            except ValueError as exc:
                raise ValueError(f'Line {line}: date must be ISO YYYY-MM-DD') from exc
            if row['source'] not in ('google','meta','tiktok'):
                raise ValueError(f'Line {line}: source must be google, meta or tiktok')
            if len(row['currency']) != 3 or not row['currency'].isascii() or not row['currency'].isupper() or not row['currency'].isalpha():
                raise ValueError(f'Line {line}: use a three-letter uppercase currency code')
            if not row['campaign_id'] or not row['campaign']:
                raise ValueError(f'Line {line}: campaign ID and name required')
            key = (row['date'],row['source'],row['campaign_id'],row['currency'])
            if key in seen:
                raise ValueError(f'Line {line}: duplicate daily campaign key')
            seen.add(key)
            for field in NUMERIC:
                row[field] = None if field == 'conversion_value' and row[field] == '' else number(row[field],field,line)
            rows.append(row)
    if not rows:
        raise ValueError('CSV contains no data rows')
    return rows

def ratio(top, bottom, factor=Decimal(1)):
    return None if bottom == 0 else (top / bottom * factor).quantize(Decimal('0.01'))

def summarize(rows):
    groups = {}
    for row in rows:
        key = (row['source'],row['currency'],row['campaign_id'])
        if key not in groups:
            groups[key] = {k:row[k] for k in ('source','currency','campaign_id','campaign')}
            groups[key].update({k:Decimal(0) for k in NUMERIC})
            groups[key]['value_complete'] = True
            groups[key]['dates'] = set()
        g = groups[key]
        g['dates'].add(row['date'])
        for field in NUMERIC:
            if row[field] is None:
                g['value_complete'] = False
            else:
                g[field] += row[field]
    output = []
    for _, g in sorted(groups.items()):
        dates = sorted(g.pop('dates'))
        g['period_start'],g['period_end'] = dates[0],dates[-1]
        g['reported_days'] = len(dates)
        if not g.pop('value_complete'):
            g['conversion_value'] = None
        g['ctr_pct'] = ratio(g['clicks'],g['impressions'],Decimal(100))
        g['cpc'] = ratio(g['spend'],g['clicks'])
        g['cost_per_platform_conversion'] = ratio(g['spend'],g['conversions'])
        g['platform_roas'] = None if g['conversion_value'] is None else ratio(g['conversion_value'],g['spend'])
        g['checks'] = []
        if g['clicks'] == 0 and g['spend'] > 0:
            g['checks'].append('Spend with zero clicks: check export definitions and delivery; not proof of waste.')
        if g['spend'] > 0 and g['conversions'] == 0:
            g['checks'].append('No platform conversions recorded: verify goal definitions, attribution delay and tracking before changing spend.')
        if g['conversion_value'] is None:
            g['checks'].append('Conversion value missing for at least one row; ROAS unavailable.')
        if g['clicks'] > g['impressions']:
            g['checks'].append('Clicks exceed impressions: confirm metric definitions and export mapping.')
        output.append(g)
    return {'schema_version':1,'mode':'offline','campaigns':output,'limitations':[
        'Platform-attributed conversions are not verified unique leads, sales, profit or cash receipts.',
        'Do not add conversions or conversion value across platforms: attribution may overlap.',
        'Currencies are kept separate; no exchange-rate conversion is performed.',
        'The export cannot prove that conversion tracking or consent is installed correctly.',
        'Account timezones, date ranges and attribution windows must be agreed before comparison.',
        'Flags are review questions, not campaign recommendations or causal conclusions.'
    ]}

def serializable(value):
    if isinstance(value, Decimal):
        return format(value, 'f')
    raise TypeError(type(value).__name__)

def render(data, label):
    esc = html.escape
    def fmt(value):
        return 'Not available' if value is None else esc(str(value))
    cards = []
    for g in data['campaigns']:
        metrics = [('Spend',g['spend']),('Clicks',g['clicks']),('CTR %',g['ctr_pct']),('CPC',g['cpc']),('Platform conversions',g['conversions']),('Cost / conversion',g['cost_per_platform_conversion']),('Platform conversion value',g['conversion_value']),('Platform ROAS',g['platform_roas'])]
        cells = ''.join('<div class="metric"><span>'+name+'</span><strong>'+fmt(value)+'</strong></div>' for name,value in metrics)
        flags = ''.join('<li>'+esc(t)+'</li>' for t in g['checks']) or '<li>No rule-based review flags. This is not an audit pass.</li>'
        cards.append('<article><div class="eyebrow">'+esc(g['source'].upper())+' / '+esc(g['currency'])+'</div><h2>'+esc(g['campaign'])+'</h2><p>'+esc(g['period_start'])+' to '+esc(g['period_end'])+' · '+str(g['reported_days'])+' reported dates</p><div class="grid">'+cells+'</div><h3>Questions to review</h3><ul>'+flags+'</ul></article>')
    limits = ''.join('<li>'+esc(t)+'</li>' for t in data['limitations'])
    return '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Campaign Evidence — Export Report</title><style>body{margin:0;background:#f3f5f6;color:#142a38;font:16px/1.6 system-ui,sans-serif}main{max-width:1100px;margin:auto;padding:40px 22px}header{background:#102f3e;color:white;padding:36px;border-radius:18px}h1{font-size:clamp(2rem,5vw,3.5rem);line-height:1.1;letter-spacing:-.045em;margin:12px 0}h2{margin:8px 0;font-size:1.55rem}h3{font-size:1rem;margin-top:26px}.eyebrow{font-size:.75rem;letter-spacing:.14em;font-weight:700;color:#197a68}header .eyebrow{color:#9be3cb}.badge{display:inline-block;padding:6px 12px;border:1px solid #94c9b8;border-radius:30px;font-size:.8rem}article,aside{background:white;padding:30px;margin:24px 0;border:1px solid #dce4e8;border-radius:16px}.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px;margin:24px 0}.metric span{display:block;font-size:.78rem;color:#516573}.metric strong{font-size:1.6rem;font-weight:650;overflow-wrap:anywhere}li{margin:8px 0}p{color:#516573}header p{color:#d2e5e9}footer{font-size:.85rem;color:#516573}@media(max-width:640px){main{padding:16px}header,article,aside{padding:22px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.metric strong{font-size:1.3rem}}</style><main><header><div class="eyebrow">CAMPAIGN EVIDENCE / OFFLINE EXPORT QA</div><h1>Know what the numbers actually say.</h1><p>One readable view of campaign exports, missing data and the questions to resolve next.</p><span class="badge">'+esc(label)+'</span></header>'+''.join(cards)+'<aside><h2>Read before making a decision</h2><ul>'+limits+'</ul><p>No account connection, AI API call, tracking tag or campaign change was made.</p></aside><footer>Built by Ivan Shevchuk · Personal technical demonstration · Rules-based calculations; no AI-generated recommendations.</footer></main></html>'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input',type=Path)
    p.add_argument('--output',type=Path,default=Path('output'))
    p.add_argument('--label',required=True,help='Use FICTIONAL DEMO DATA for the supplied fixture')
    args = p.parse_args()
    try:
        data = summarize(load_rows(args.input))
    except (ValueError,OSError) as exc:
        p.exit(2,f'Input error: {exc}\n')
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'report.json').write_text(json.dumps(data,default=serializable,indent=2),encoding='utf-8')
    (args.output/'report.html').write_text(render(data,args.label),encoding='utf-8')
    brief = {'instruction':'Review aggregates only. Cite campaign IDs and supplied figures. Distinguish observation from hypothesis. Ask about missing attribution/CRM context. Never infer profit, unique sales or prescribe spend changes from this export alone. No campaign writes. Human review required.','data':data}
    (args.output/'ai-review-brief.json').write_text(json.dumps(brief,default=serializable,indent=2),encoding='utf-8')
    print(f'Created report.html, report.json and ai-review-brief.json in {args.output}')

if __name__ == '__main__':
    main()
