"""Read-only CSV join preflight. AI-assisted personal demonstration, not client work."""
import argparse
import csv
import json
from pathlib import Path


class InputError(ValueError):
    pass


def load_keys(path, key, label, max_rows=100000):
    """Validate a one-record-per-key export before any join can multiply rows."""
    keys = set()
    try:
        with Path(path).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            headers = reader.fieldnames
            if not headers or any(not h.strip() for h in headers):
                raise InputError(f"{label}: missing or blank headers")
            if len(set(headers)) != len(headers):
                raise InputError(f"{label}: duplicate column names")
            if key not in headers:
                raise InputError(f"{label}: required key column is missing")
            for row_number, row in enumerate(reader, start=2):
                if row_number - 1 > max_rows:
                    raise InputError(f"{label}: row limit exceeded")
                if None in row or any(value is None for value in row.values()):
                    raise InputError(f"{label}: inconsistent column count at row {row_number}")
                identifier = row[key].strip()
                if not identifier:
                    raise InputError(f"{label}: empty key at row {row_number}")
                if identifier in keys:
                    raise InputError(f"{label}: duplicate key at row {row_number}")
                keys.add(identifier)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InputError(f"{label}: unreadable or malformed CSV") from exc
    return keys


def reconcile(left, right, left_key, right_key, max_rows=100000):
    if max_rows < 1:
        raise InputError("row limit must be positive")
    a = load_keys(left, left_key, "left", max_rows)
    b = load_keys(right, right_key, "right", max_rows)
    return {
        "schema_version": 1,
        "left_records": len(a),
        "right_records": len(b),
        "matched_keys": len(a & b),
        "left_only_keys": len(a - b),
        "right_only_keys": len(b - a),
        "policy": "unique keys; whitespace trimmed; leading zeros preserved",
        "limitations": "Key overlap only; not proof of correct attribution or financial results",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--left-key", required=True)
    parser.add_argument("--right-key", required=True)
    parser.add_argument("--max-rows", type=int, default=100000)
    args = parser.parse_args(argv)
    try:
        result = reconcile(args.left, args.right, args.left_key, args.right_key, args.max_rows)
    except InputError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    print(json.dumps({"ok": True, **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
