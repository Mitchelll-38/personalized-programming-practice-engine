"""Audit canonical JSONL and create research examples without fitting transforms."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .pipeline import audit, prediction_examples, student_split
from .schema import Interaction
from .manifest import ProcessingManifest, write_manifest
from .codeworkout import import_codeworkout
from .holdouts import family_holdout


def _unique_mapping(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate family mapping key: {key}")
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Canonical JSONL, or release directory with --format codeworkout")
    parser.add_argument("--format", choices=("canonical", "codeworkout"), default="canonical")
    parser.add_argument("--catalog", type=Path, help="Required independently supplied candidate catalog for CodeWorkout")
    parser.add_argument("--output", type=Path, default=Path("data/processed/day1"))
    parser.add_argument("--seed", type=int, default=38)
    parser.add_argument("--dataset-version", default="unverified-local", help="Explicit release/fixture identifier; does not verify terms")
    parser.add_argument("--synthetic", action="store_true", help="Declare this input to be synthetic fixture data")
    parser.add_argument("--split-protocol", choices=("student", "family"), default="student")
    parser.add_argument("--family-map", type=Path, help="JSON problem-to-family mapping; required only for family splits")
    args = parser.parse_args()
    if args.split_protocol == "family" and args.family_map is None:
        parser.error("--family-map is required for --split-protocol family")
    if args.split_protocol == "student" and args.family_map is not None:
        parser.error("--family-map is only valid for --split-protocol family")
    if args.output.exists() or args.output.is_symlink():
        raise ValueError("Processing output must be a new directory")
    import_report = None
    if args.format == "codeworkout":
        if args.catalog is None:
            parser.error("--catalog is required for --format codeworkout")
        imported = import_codeworkout(args.input, args.catalog)
        rows = imported.rows
        source_bytes = "".join(row.model_dump_json() + "\n" for row in rows).encode("utf-8")
        paths = {"MainTable.csv": args.input / "MainTable.csv", "catalog.json": args.catalog}
        code_path = args.input / "CodeStates/CodeStates.csv"
        if code_path.exists():
            paths["CodeStates/CodeStates.csv"] = code_path
        import_report = {**imported.audit,
                         "source_sha256": {name: sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}}
    else:
        if args.catalog is not None:
            parser.error("--catalog is only valid for --format codeworkout")
        source_bytes = args.input.read_bytes()
        rows = [Interaction.model_validate_json(line) for line in source_bytes.decode("utf-8-sig").splitlines() if line.strip()]
    # Validate all artifacts before writing anything.
    report = audit(rows, source_bytes)
    if import_report is not None:
        report["import"] = import_report
        report["label_definition"] = import_report["label_definition"]
        report["ordering"] = import_report["ordering"]
        report["source_hash_definition"] = "Canonical reconstructed JSONL; original table/catalog hashes in import.source_sha256"
    if args.split_protocol == "family":
        map_bytes = args.family_map.read_bytes()
        mapping = json.loads(map_bytes.decode("utf-8-sig"), object_pairs_hook=_unique_mapping)
        if not isinstance(mapping, dict) or any(
            not key.strip() or not isinstance(value, str) or not value.strip()
            for key, value in mapping.items()
        ):
            raise ValueError("Family map must be a JSON object of nonempty string IDs")
        held_out = family_holdout(rows, mapping, args.seed)
        split, partitions = held_out.metadata, held_out.examples
        report["family_map_sha256"] = split["family_map_sha256"] = sha256(map_bytes).hexdigest()
    else:
        split = student_split(rows, args.seed)
        examples = prediction_examples(rows)
        partitions = {group: [example for example in examples if example.student_id in student_ids]
                      for group, student_ids in split["student_ids"].items()}
    split["source_sha256"] = report["source_sha256"]
    manifest = ProcessingManifest(dataset_version=args.dataset_version,
                                  source_kind="synthetic" if args.synthetic else "unverified",
                                  source_sha256=report["source_sha256"], seed=args.seed,
                                  split_version=split["version"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lock = args.output.with_name(f".{args.output.name}.publish-lock")
    lock.mkdir()
    try:
        with TemporaryDirectory(prefix=f".{args.output.name}.", dir=args.output.parent) as temporary:
            staging = Path(temporary)
            for name, value in (("audit.json", report), ("split.json", split)):
                (staging / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
            for group, selected in partitions.items():
                (staging / f"{group}.jsonl").write_text(
                    "".join(example.model_dump_json() + "\n" for example in selected), encoding="utf-8")
            write_manifest(staging, manifest)
            if args.output.exists() or args.output.is_symlink():
                raise ValueError("Processing output must be a new directory")
            os.rename(staging, args.output)
    finally:
        lock.rmdir()
    print(json.dumps({"output": str(args.output), "audit": report, "manifest_version": manifest.manifest_version}, indent=2))


if __name__ == "__main__":
    main()
