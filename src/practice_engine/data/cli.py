"""Audit canonical JSONL and create research examples without fitting transforms."""

import argparse
import json
from pathlib import Path

from .pipeline import audit, prediction_examples, student_split
from .schema import Interaction


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Canonical UTF-8 JSONL (not raw ProgSnap2 logs)")
    parser.add_argument("--output", type=Path, default=Path("data/processed/day1"))
    parser.add_argument("--seed", type=int, default=38)
    args = parser.parse_args()
    source_bytes = args.input.read_bytes()
    rows = [Interaction.model_validate_json(line) for line in source_bytes.decode("utf-8-sig").splitlines() if line.strip()]
    # Validate all artifacts before writing anything.
    report = audit(rows, source_bytes)
    split = student_split(rows, args.seed)
    split["source_sha256"] = report["source_sha256"]
    examples = prediction_examples(rows)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("audit.json", report), ("split.json", split)):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    for group, student_ids in split["student_ids"].items():
        selected = [example for example in examples if example.student_id in student_ids]
        (args.output / f"{group}.jsonl").write_text(
            "".join(example.model_dump_json() + "\n" for example in selected), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "audit": report}, indent=2))


if __name__ == "__main__":
    main()
