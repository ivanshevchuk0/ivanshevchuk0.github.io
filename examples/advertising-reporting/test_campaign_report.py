import csv, json, subprocess, sys, tempfile, unittest
from pathlib import Path
from decimal import Decimal
import campaign_report as app

BASE = Path(__file__).parent
class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'input.csv'
        with (BASE/'fictional-campaigns.csv').open() as f:
            self.rows = list(csv.DictReader(f))
    def write(self, rows=None, headers=None):
        rows = self.rows if rows is None else rows
        with self.path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=headers or list(self.rows[0]))
            w.writeheader(); w.writerows(rows)
        return self.path
    def report(self):
        return app.summarize(app.load_rows(self.write()))
    def test_weighted_ratios_and_preserved_id(self):
        g=self.report()['campaigns'][0]
        self.assertEqual(g['campaign_id'],'001')
        self.assertEqual(g['ctr_pct'],Decimal('2.50'))
        self.assertEqual(g['cpc'],Decimal('2.00'))
        self.assertEqual(g['cost_per_platform_conversion'],Decimal('40.00'))
        self.assertEqual(g['reported_days'],2)
    def test_no_cross_currency_or_platform_totals(self):
        r=self.report()
        self.assertNotIn('total_conversions',r)
        self.assertEqual({g['currency'] for g in r['campaigns']},{'EUR','PLN'})
        t=r['campaigns'][2]
        self.assertEqual(t['platform_roas'],Decimal('1.50'))
    def test_zero_conversions_not_infinity(self):
        g=self.report()['campaigns'][1]
        self.assertIsNone(g['cost_per_platform_conversion'])
        self.assertIn('No platform conversions',g['checks'][0])
    def test_partial_missing_value_disables_roas(self):
        self.rows[0]['conversion_value']='200'
        self.assertIsNone(self.report()['campaigns'][0]['platform_roas'])
    def test_duplicate_daily_record_rejected(self):
        self.rows.append(self.rows[0].copy())
        with self.assertRaisesRegex(ValueError,'duplicate daily'):
            app.load_rows(self.write())
    def test_nonfinite_negative_and_fractional_counts_rejected(self):
        for field,value in [('spend','NaN'),('spend','Infinity'),('spend','-1'),('clicks','0.5')]:
            with self.subTest(field=field,value=value):
                old=self.rows[0][field]; self.rows[0][field]=value
                with self.assertRaises(ValueError): app.load_rows(self.write())
                self.rows[0][field]=old
    def test_fractional_attribution_allowed(self):
        self.rows[0]['conversions']='0.5'
        self.assertEqual(self.report()['campaigns'][0]['conversions'],Decimal('3.5'))
    def test_extra_personal_data_column_rejected(self):
        for row in self.rows: row['email']='fiction@example.invalid'
        with self.assertRaisesRegex(ValueError,'unexpected fields'):
            app.load_rows(self.write())
    def test_invalid_date_currency_and_source_rejected(self):
        for field,value in [('date','20261001'),('date','2026-02-30'),('currency','pln'),('source','other')]:
            with self.subTest(field=field):
                old=self.rows[0][field]; self.rows[0][field]=value
                with self.assertRaises(ValueError): app.load_rows(self.write())
                self.rows[0][field]=old
    def test_empty_input_and_zero_denominators(self):
        with self.assertRaisesRegex(ValueError,'no data'): app.load_rows(self.write([]))
        self.assertIsNone(app.ratio(Decimal(1),Decimal(0)))
    def test_html_escapes_campaign_and_label(self):
        self.rows[0]['campaign']='<script>alert(1)</script>'
        content=app.render(self.report(),'<img src=x onerror=alert(1)>')
        self.assertNotIn('<script>',content)
        self.assertNotIn('<img ',content)
        self.assertIn('&lt;script&gt;',content)
    def test_cli_outputs_and_bad_input_failure(self):
        output=Path(self.tmp.name)/'out'
        p=subprocess.run([sys.executable,str(BASE/'campaign_report.py'),str(self.write()),'--output',str(output),'--label','FICTIONAL DEMO DATA'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(json.loads((output/'report.json').read_text())['campaigns']),3)
        self.assertIn('Human review required', (output/'ai-review-brief.json').read_text())
        self.rows[0]['spend']='invalid'
        p=subprocess.run([sys.executable,str(BASE/'campaign_report.py'),str(self.write()),'--output',str(output),'--label','TEST'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2)
        self.assertIn('Input error',p.stderr)
if __name__ == '__main__': unittest.main()
