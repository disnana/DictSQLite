"""
Convert benchmark_results.csv into github-action-benchmark custom JSON.

The action expects:
[
  {"name": "case name", "unit": "ops/sec", "value": 123.4, "extra": "..."}
]
"""

import argparse
import csv
import json
import os


def make_name(row):
    parts = [
        row.get("category", "unknown"),
        row.get("operation", "unknown"),
        row.get("scenario", "legacy"),
        row.get("persist_mode", "unknown"),
        row.get("storage_mode", "unknown"),
        f"size={row.get('data_size', '0')}",
        f"batch={row.get('batch_size', '1')}",
    ]
    table_mode = row.get("table_mode", "")
    if table_mode and table_mode != "prefix":
        parts.append(f"table={table_mode}")
    return " / ".join(parts)


def convert(input_path, output_path):
    records = []
    with open(input_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                value = float(row["ops_per_sec"])
            except (KeyError, TypeError, ValueError):
                continue

            extra = (
                f"avg={row.get('avg_time_ms', 'n/a')}ms, "
                f"p95={row.get('p95_time_ms', row.get('max_time_ms', 'n/a'))}ms, "
                f"iterations={row.get('iterations', 'n/a')}"
            )
            records.append(
                {
                    "name": make_name(row),
                    "unit": "ops/sec",
                    "value": value,
                    "extra": extra,
                }
            )

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        f.write("\n")

    print(f"Exported {len(records)} benchmark records to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="benchmark_results.csv")
    parser.add_argument("output", help="github-action-benchmark JSON output")
    args = parser.parse_args()
    convert(args.input, args.output)


if __name__ == "__main__":
    main()
