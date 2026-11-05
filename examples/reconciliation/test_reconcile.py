import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from reconcile import InputError, main, reconcile


class ReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.left = Path(self.tmp.name) / "left.csv"
        self.right = Path(self.tmp.name) / "right.csv"

    def write(self, left="id,name\n001,Alpha\n002,Beta\n", right="lead_id,status\n001,paid\n003,new\n"):
        self.left.write_text(left, encoding="utf-8")
        self.right.write_text(right, encoding="utf-8")

    def run_audit(self, **kwargs):
        return reconcile(self.left, self.right, "id", "lead_id", **kwargs)

    def test_match_and_unmatched_counts(self):
        self.write()
        r = self.run_audit()
        self.assertEqual((r["matched_keys"], r["left_only_keys"], r["right_only_keys"]), (1, 1, 1))

    def test_leading_zeros_are_not_coerced(self):
        self.write("id\n001\n", "lead_id\n1\n")
        self.assertEqual(self.run_audit()["matched_keys"], 0)

    def test_duplicate_keys_stop_join_amplification(self):
        self.write(right="lead_id\n001\n001\n")
        with self.assertRaisesRegex(InputError, "right: duplicate key"):
            self.run_audit()

    def test_empty_key_is_rejected(self):
        self.write("id,name\n ,Alpha\n")
        with self.assertRaisesRegex(InputError, "empty key"):
            self.run_audit()

    def test_duplicate_header_is_rejected(self):
        self.write("id,id\n001,002\n")
        with self.assertRaisesRegex(InputError, "duplicate column"):
            self.run_audit()

    def test_ragged_records_are_rejected(self):
        for text in ("id,name\n001\n", "id,name\n001,Alpha,extra\n"):
            with self.subTest(text=text):
                self.write(text)
                with self.assertRaisesRegex(InputError, "column count"):
                    self.run_audit()

    def test_utf8_bom_and_whitespace(self):
        self.write("\ufeffid,name\n 001 ,Zażółć\n")
        self.assertEqual(self.run_audit()["matched_keys"], 1)

    def test_missing_key_and_row_limit(self):
        self.write("other\n001\n")
        with self.assertRaisesRegex(InputError, "key column"):
            self.run_audit()
        self.write()
        with self.assertRaisesRegex(InputError, "row limit"):
            self.run_audit(max_rows=1)

    def test_cli_summary_no_raw_identifiers_and_no_source_changes(self):
        self.write()
        before = (self.left.read_bytes(), self.right.read_bytes())
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.left), str(self.right), "--left-key", "id", "--right-key", "lead_id"])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        self.assertNotIn("Alpha", output.getvalue())
        self.assertEqual(before, (self.left.read_bytes(), self.right.read_bytes()))

    def test_cli_error_exit_and_no_results_on_invalid_input(self):
        self.write("id\n001\n001\n")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(self.left), str(self.right), "--left-key", "id", "--right-key", "lead_id"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertFalse(result["ok"])
        self.assertNotIn("matched_keys", result)


if __name__ == "__main__":
    unittest.main()
