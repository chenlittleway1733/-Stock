"""Validate model stock dataset files before model-library updates.

Usage:
    python tools/validate_stock_dataset_file.py path/to/M07.xlsx
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from validators.stock_dataset_batch import validate_stock_dataset_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate stock model dataset CSV/XLSX files.")
    parser.add_argument("input_file", help="CSV/XLSX file to validate")
    parser.add_argument("--sheet", default="", help="Excel sheet name; leave blank for auto-detect")
    parser.add_argument("--output-dir", default="output/validation", help="Directory for CSV/JSON reports")
    args = parser.parse_args()

    result = validate_stock_dataset_file(
        args.input_file,
        preferred_sheet=args.sheet.strip() or None,
        output_dir=args.output_dir,
    )
    payload = {
        "summary": result["summary"],
        "artifact_paths": result["artifact_paths"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
