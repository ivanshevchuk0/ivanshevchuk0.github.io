"""Human-verified public lead research and an editable Excel sales tracker (Python 3.12)."""
from __future__ import annotations

import argparse
import json
import re
import textwrap
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.formatting.rule import FormulaRule
from openpyxl.workbook.properties import CalcProperties
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent
PERMISSION = ['Unknown', 'Confirmed', 'Not permitted']
CONTACT = ['Not Contacted', 'Contacted', 'Interested', 'Not Interested', 'Callback Requested', 'No Answer', 'Do Not Contact']
DEALS = ['Not Started', 'Discussion', 'Proposal Sent', 'Approved', 'Rejected', 'Closed Won']
PRIORITIES = ['High', 'Medium', 'Low']
WEBSITE = ['Missing', 'Poor', 'Average', 'Good']
RESEARCH = [
    ('name', 'Business name'), ('category', 'Business category'), ('address', 'Address'),
    ('district', 'District'), ('phone', 'Business phone'), ('website', 'Website URL'),
    ('instagram', 'Instagram URL'), ('facebook', 'Facebook URL'), ('maps', 'Google Maps URL'),
    ('booksy', 'Booksy URL'), ('website_status', 'Website status'),
    ('opportunity', 'Website improvement opportunity'), ('priority', 'Lead priority'),
    ('phone_source', 'Phone source URL'), ('verified_on', 'Date verified'),
]
SALES = ['Contact permission', 'Contact status', 'Called on', 'Follow-up date',
         'Decision maker contacted', 'Website offer (PLN)', 'Deal status', 'Notes']
EVIDENCE = [
    ('business_source', 'Business and address source URL'),
    ('website_evidence', 'Website assessment evidence'), ('research_notes', 'Research notes'),
    ('district_source', 'District source URL'), ('social_source', 'Social profile source URL'),
    ('id', 'Lead ID'),
]
HEADERS = [v for _, v in RESEARCH] + SALES + [v for _, v in EVIDENCE]
LINK_KEYS = {'website', 'instagram', 'facebook', 'maps', 'booksy', 'phone_source',
             'business_source', 'district_source', 'social_source'}
NAVY, BLUE, AMBER = '26344A', '2463A8', 'FFF5DB'


def validate_url(value: str, label: str) -> None:
    if value and (urlsplit(value).scheme not in {'http', 'https'} or not urlsplit(value).netloc):
        raise ValueError(f'{label}: expected an absolute public HTTP(S) URL')


def load_leads(path: Path) -> list[dict]:
    leads = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(leads, list) or not leads:
        raise ValueError('Research must contain a non-empty list of verified business records')
    seen_ids, seen_phones, seen_locations = set(), set(), set()
    for lead in leads:
        for key in ['id', 'name', 'category', 'address', 'district', 'phone', 'phone_source',
                    'business_source', 'district_source', 'verified_on', 'opportunity', 'website_evidence']:
            if not isinstance(lead.get(key), str) or not lead[key].strip():
                raise ValueError(f'Missing {key} for {lead.get("name", "unnamed lead")}')
        if 'krak' not in lead['address'].casefold():
            raise ValueError(f'{lead["name"]}: address is outside the Kraków research scope')
        if not re.fullmatch(r'\+48\s?(?:\d\s?){9}', lead['phone']):
            raise ValueError(f'{lead["name"]}: expected +48 and nine Polish telephone digits')
        verified = date.fromisoformat(lead['verified_on'])
        if verified > date.today():
            raise ValueError(f'{lead["name"]}: verification date is in the future')
        if lead.get('priority') not in PRIORITIES or lead.get('website_status') not in WEBSITE:
            raise ValueError(f'{lead["name"]}: invalid priority or website status')
        if lead['website_status'] == 'Missing' and lead.get('website'):
            raise ValueError(f'{lead["name"]}: Missing status conflicts with a dedicated website URL')
        if lead['website_status'] != 'Missing' and not lead.get('website'):
            raise ValueError(f'{lead["name"]}: website rating requires an observed website URL')
        for key in LINK_KEYS:
            validate_url(lead.get(key, ''), key)
        phone = re.sub(r'\D', '', lead['phone'])
        location = (lead['name'].casefold().strip(), lead['address'].casefold().strip())
        if lead['id'] in seen_ids or phone in seen_phones or location in seen_locations:
            raise ValueError(f'Duplicate identity, telephone or name/address: {lead["name"]}')
        seen_ids.add(lead['id']); seen_phones.add(phone); seen_locations.add(location)
    return sorted(leads, key=lambda x: (PRIORITIES.index(x['priority']), x.get('rank', 999), x['name']))


def maps_link(lead: dict) -> str:
    """An explicit address-search navigation URL, not a claimed Google place ID."""
    return 'https://www.google.com/maps/search/?api=1&query=' + quote(lead['name'] + ', ' + lead['address'])


def read_sales(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    wb = load_workbook(path)
    ws = wb['Leads']
    indices = {c.value: c.column for c in ws[1]}
    if 'Lead ID' not in indices:
        raise ValueError('Existing workbook has no Lead ID; cannot safely preserve sales records')
    result = {}
    for row in range(2, ws.max_row + 1):
        identity = ws.cell(row, indices['Lead ID']).value
        if not identity:
            continue
        if identity in result:
            raise ValueError(f'Duplicate Lead ID in existing workbook: {identity}')
        result[identity] = {h: ws.cell(row, indices[h]).value for h in SALES}
    return result


def dropdown(ws, column: str, values: list[str], last: int) -> None:
    dv = DataValidation(type='list', formula1='"' + ','.join(values) + '"', allow_blank=True)
    dv.errorTitle = 'Choose a listed value'
    dv.error = 'Use the dropdown options for this field.'
    dv.showErrorMessage = True
    dv.errorStyle = 'stop'
    dv.showDropDown = False
    ws.add_data_validation(dv)
    dv.add(f'{column}2:{column}{last}')


def shade(ws, column: str, value: str, color: str, last: int) -> None:
    ws.conditional_formatting.add(f'{column}2:{column}{last}', FormulaRule(
        formula=[f'${column}2="{value}"'], fill=PatternFill('solid', fgColor=color)))


def dashboard(wb: Workbook, leads: list[dict]) -> None:
    ws = wb.create_sheet('Dashboard')
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = NAVY
    ws['A2'] = 'Kraków business prospects'
    ws['A2'].font = Font(name='Arial', size=16, bold=True, color=NAVY)
    ws['A3'] = 'Latest research review ' + max(x['verified_on'] for x in leads)
    ws['A3'].font = Font(name='Arial', size=10, italic=True, color='64748B')
    ws.append([])
    ws['A5'], ws['B5'], ws['C5'] = 'Metric', 'Value', 'Definition'
    n, p, q, r, s, v, u = [f'LeadsTable[{x}]' for x in [
        'Business name', 'Contact permission', 'Contact status', 'Called on',
        'Follow-up date', 'Deal status', 'Website offer (PLN)']]
    contacted = '+'.join(f'COUNTIF({q},"{x}")' for x in CONTACT[1:6])
    contacted += f'+COUNTIFS({q},"Do Not Contact",{r},">0")+COUNTIFS({q},"Not Contacted",{r},">0")'
    due = f'COUNTIFS({s},">0",{s},"<="&TODAY(),{p},"Confirmed",{q},"<>Do Not Contact",{q},"<>Not Interested",{v},"<>Rejected",{v},"<>Closed Won")'
    due += f'+COUNTIFS({q},"Callback Requested",{s},"",{p},"Confirmed",{v},"<>Rejected",{v},"<>Closed Won")'
    metrics = [
        ('Total leads', f'=COUNTA({n})', 'Named businesses in the Leads table.'),
        ('High-priority leads', '=COUNTIF(LeadsTable[Lead priority],"High")', 'Highest priority website opportunities.'),
        ('Contacted businesses', '=' + contacted, 'Contact attempted, or an actual call date recorded.'),
        ('Interested businesses', f'=COUNTIF({q},"Interested")', 'Current contact status is Interested.'),
        ('Rejected businesses', f'=COUNTIF({q},"Not Interested")+COUNTIF({v},"Rejected")-COUNTIFS({q},"Not Interested",{v},"Rejected")', 'Not Interested or Rejected, counted once.'),
        ('Follow-ups required', '=' + due, 'Due/overdue or undated callbacks; confirmed permission only; closed/rejected/DNC excluded.'),
        ('Proposals sent', f'=COUNTIF({v},"Proposal Sent")', 'Current deal stage is Proposal Sent.'),
        ('Deals won', f'=COUNTIF({v},"Closed Won")', 'Current deal stage is Closed Won.'),
        ('Potential deal value', '=' + '+'.join(f'SUMIFS({u},{v},"{stage}")' for stage in ['Discussion', 'Proposal Sent', 'Approved']), 'PLN offers in Discussion, Proposal Sent or Approved; blank offers contribute zero.'),
    ]
    for row, (label, formula, definition) in enumerate(metrics, 6):
        ws.cell(row, 1, label)
        ws.cell(row, 2, formula)
        ws.cell(row, 3, definition)
        ws.cell(row, 2).number_format = '#,##0' if row < 14 else '#,##0.00 "PLN"'
        ws.row_dimensions[row].height = 36 if row in {11, 14} else 29
    ws['A17'] = 'Working with the tracker'
    ws['A17'].font = Font(name='Arial', size=12, bold=True, color=NAVY)
    guidance = [
        'Amber cells in Leads are editable sales fields. All leads start with permission Unknown.',
        'Missing means no independent website found in checked sources, not proof that none exists.',
        'Blank social/Booksy links mean not verified. Google Maps links are generated address searches.',
        'Research is a public-listing review, not a telephone check or confirmation of permission.',
    ]
    for row, text in enumerate(guidance, 18):
        ws.cell(row, 1, text)
        ws.row_dimensions[row].height = 22
    ws.column_dimensions['A'].width = 30
    ws.column_dimensions['B'].width = 17
    ws.column_dimensions['C'].width = 94
    for row in ws.iter_rows(min_row=5, max_row=14):
        for c in row:
            c.font = Font(name='Arial', size=10, color=NAVY)
            c.alignment = Alignment(vertical='center', wrap_text=True, indent=1 if c.column == 3 else 0)
            if c.row > 5 and c.row % 2 == 0:
                c.fill = PatternFill('solid', fgColor='F2F5FA')
    for c in ws[5]:
        c.fill = PatternFill('solid', fgColor=NAVY)
        c.font = Font(name='Arial', size=10, color='FFFFFF', bold=True)
        c.alignment = Alignment(horizontal='center', vertical='center')
    for row in range(6, 15):
        ws.cell(row, 2).font = Font(name='Arial', size=12, bold=True, color=NAVY)
        ws.cell(row, 2).alignment = Alignment(horizontal='right', vertical='center')
    for row in range(18, 22):
        ws.cell(row, 1).font = Font(name='Arial', size=10, color='64748B')
    ws.print_options.horizontalCentered = True
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = ws.page_setup.fitToHeight = 1
    ws.print_area = 'A1:C22'


def generate(leads: list[dict], output: Path, preserve: bool = True) -> None:
    previous = read_sales(output) if preserve else {}
    missing = set(previous) - {lead['id'] for lead in leads}
    if missing:
        raise ValueError('Refresh would remove existing sales records: ' + ', '.join(sorted(missing)) +
                         '. Retain those leads or use a separate --output path.')
    wb = Workbook()
    wb.calculation = CalcProperties(calcId=191029, fullCalcOnLoad=True, forceFullCalc=True, calcMode='auto')
    ws = wb.active
    ws.title = 'Leads'
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = BLUE
    ws.append(HEADERS)
    for lead in leads:
        default_sales = {'Contact permission': 'Unknown', 'Contact status': 'Not Contacted', 'Deal status': 'Not Started'}
        default_sales.update(previous.get(lead['id'], {}))
        data = dict(lead, maps=lead.get('maps') or maps_link(lead))
        research = [date.fromisoformat(data[key]) if key == 'verified_on' else data.get(key, '') for key, _ in RESEARCH]
        ws.append(research + [default_sales.get(h) for h in SALES] + [data.get(k, '') for k, _ in EVIDENCE])
    last = ws.max_row
    table = Table(displayName='LeadsTable', ref=f'A1:AC{last}')
    table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = 'B2'
    ws.row_dimensions[1].height = 38
    widths = [31, 26, 38, 25, 20, 31, 31, 31, 36, 44, 17, 69, 15, 45, 16,
              21, 23, 16, 16, 27, 22, 23, 40, 44, 69, 69, 42, 43, 23]
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    for row in ws.iter_rows():
        for c in row:
            c.font = Font(name='Arial', size=10, color=NAVY)
            c.alignment = Alignment(vertical='top', wrap_text=True)
            if c.row == 1:
                c.fill = PatternFill('solid', fgColor=NAVY)
                c.font = Font(name='Arial', size=10, color='FFFFFF', bold=True)
                c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                c.border = Border(right=Side(style='thin', color='FFFFFF'))
            elif 16 <= c.column <= 23:
                c.fill = PatternFill('solid', fgColor=AMBER)
            if c.row > 1 and isinstance(c.value, str):
                if c.value.startswith(('http://', 'https://')):
                    c.hyperlink = c.value
                    c.font = Font(name='Arial', size=10, color=BLUE, underline='single')
                elif c.value.startswith(('=', '+', '-', '@')):
                    c.data_type = 's'  # Prevent formula injection and keep +48 as literal text.
    for row in range(2, last + 1):
        ws.cell(row, 9).value = 'Maps address search'
        # The generated URL remains the clickable target; the JSON/source address is authoritative.
        lines = max(len(textwrap.wrap(str(c.value or ''), width=max(12, int(widths[c.column - 1] * 1.02)))) or 1
                    for c in ws[row])
        ws.row_dimensions[row].height = max(36, 14 * lines + 8)
        ws.cell(row, 5).number_format = '@'
        for col in [15, 18, 19]:
            ws.cell(row, col).number_format = 'yyyy-mm-dd'
        ws.cell(row, 21).number_format = '#,##0.00 "PLN"'
    bound = max(last, 1001)
    for col, options in [('P', PERMISSION), ('Q', CONTACT), ('V', DEALS),
                         ('T', ['Unknown', 'Yes', 'No']), ('M', PRIORITIES), ('K', WEBSITE)]:
        dropdown(ws, col, options, bound)
    money = DataValidation(type='decimal', operator='greaterThanOrEqual', formula1=0, allow_blank=True)
    money.showErrorMessage = True; money.errorStyle = 'stop'; money.error = 'Enter a non-negative PLN amount.'
    ws.add_data_validation(money); money.add(f'U2:U{bound}')
    for col in ['R', 'S']:
        dv = DataValidation(type='date', operator='between', formula1='DATE(2020,1,1)',
                            formula2='DATE(2100,12,31)', allow_blank=True)
        dv.showErrorMessage = True; dv.errorStyle = 'stop'; dv.error = 'Enter a date between 2020 and 2100.'
        ws.add_data_validation(dv); dv.add(f'{col}2:{col}{bound}')
    for col, values in [
        ('M', [('High', 'DDEDDC'), ('Medium', 'FFF0C2'), ('Low', 'E7EBF0')]),
        ('Q', [('Interested', 'DDEDDC'), ('Not Interested', 'F9DFDF'), ('Do Not Contact', 'F9DFDF'), ('Callback Requested', 'FFF0C2')]),
        ('V', [('Closed Won', 'C8E4CB'), ('Approved', 'DDEDDC'), ('Rejected', 'F9DFDF'), ('Proposal Sent', 'DCE8F7')]),
        ('P', [('Not permitted', 'F9DFDF')]),
    ]:
        for value, color in values:
            shade(ws, col, value, color, bound)
    ws.conditional_formatting.add(f'S2:S{bound}', FormulaRule(
        formula=['AND(ISNUMBER($S2),$S2<=TODAY(),$P2="Confirmed",$Q2<>"Do Not Contact",$Q2<>"Not Interested",$V2<>"Rejected",$V2<>"Closed Won")'],
        fill=PatternFill('solid', fgColor='FFF0C2')))
    ws.print_title_rows = '1:1'
    ws.page_setup.orientation = 'landscape'
    dashboard(wb, leads)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_suffix('.tmp.xlsx')
    wb.save(staging)
    staging.replace(output)
    print(f'Created {output} with {len(leads)} leads; preserved {len(previous)} sales records.')


def refresh_tasks(leads: list[dict], output: Path) -> None:
    lines = ['# Research refresh checklist', '',
             'Review public sources manually. Do not mark a lead verified just because this file was regenerated.', '',
             'For each lead confirm the business/address, phone ownership, current website, social links and district.',
             'Record changes and the actual review date in leads.json, then regenerate the workbook.',
             'No calls, messages, login bypasses, bulk platform extraction or marketing are performed.', '']
    for lead in leads:
        query = f'"{lead["name"]}" Kraków strona internetowa telefon Instagram Facebook'
        lines += [f'## {lead["name"]}', '', f'- Last reviewed: {lead["verified_on"]}',
                  f'- [Name and website search](https://www.google.com/search?q={quote(query)})',
                  f'- [Public phone source]({lead["phone_source"]})',
                  f'- [Business/address source]({lead["business_source"]})',
                  f'- [District source]({lead["district_source"]})']
        for key in ['website', 'booksy', 'instagram', 'facebook']:
            if lead.get(key):
                lines.append(f'- [{key.title()}]({lead[key]})')
        lines += [f'- Assessment to recheck: {lead["website_evidence"]}', '']
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Created {output}; verification dates were not changed.')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate', 'refresh', 'validate'], nargs='?', default='generate')
    parser.add_argument('--input', type=Path, default=ROOT / 'leads.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    leads = load_leads(args.input)
    if args.command == 'generate':
        generate(leads, args.output or ROOT / 'krakow_beauty_leads.xlsx')
    elif args.command == 'refresh':
        refresh_tasks(leads, args.output or ROOT / 'research_refresh.md')
    else:
        print(f'Validated {len(leads)} unique leads with phone, address, website and district evidence.')


if __name__ == '__main__':
    main()
