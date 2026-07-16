"""Safely migrate existing local durable data to the private data repository.

The default invocation is a metadata-only dry run. ``--apply`` uploads changed
objects in one Git commit, reads them back, and verifies SHA-256. Local source
files are never deleted by this tool.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.private_data_store import (
    private_data_display_path,
    read_private_data_file,
    require_private_data_store,
    write_private_data_files_atomic,
)

@dataclass(frozen=True)
class MigrationObject:
    source_label: str
    destination: str
    content: bytes
    row_count: int | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content).hexdigest()


def discover_objects() -> list[MigrationObject]:
    """Return local durable objects without logging their values."""
    objects: list[MigrationObject] = []
    csv_sources = (
        ("outputs/saved_actuals.csv", "actuals/saved_actuals.csv"),
        ("outputs/history/forecast_history.csv", "history/forecast_history.csv"),
        ("outputs/history/final_actuals.csv", "history/final_actuals.csv"),
    )
    for source_label, destination in csv_sources:
        source = REPO_ROOT / source_label
        if not source.is_file() or source.stat().st_size == 0:
            continue
        content = source.read_bytes()
        objects.append(
            MigrationObject(
                source_label=source_label,
                destination=destination,
                content=content,
                row_count=_csv_row_count(content),
            )
        )

    report_dir = REPO_ROOT / "outputs" / "latest"
    if report_dir.is_dir():
        for source in sorted(report_dir.glob("daily_report_*.xlsx")):
            if not source.is_file() or source.stat().st_size == 0:
                continue
            source_label = source.relative_to(REPO_ROOT).as_posix()
            destination = f"reports/latest/{source.name}"
            content = source.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            generated_at = datetime.fromtimestamp(
                source.stat().st_mtime,
                tz=timezone.utc,
            ).isoformat()
            manifest = {
                "file_name": source.name,
                "generated_at": generated_at,
                "size_bytes": len(content),
                "sha256": digest,
                "migration_source": source_label,
            }
            objects.extend(
                (
                    MigrationObject(source_label, destination, content),
                    MigrationObject(
                        f"{source_label} (manifest)",
                        f"{destination}.manifest.json",
                        json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
                        + b"\n",
                    ),
                )
            )
    return objects


def _csv_row_count(content: bytes) -> int:
    text = content.decode("utf-8-sig")
    rows = csv.reader(io.StringIO(text))
    return max(sum(1 for _row in rows) - 1, 0)


def _print_plan(objects: list[MigrationObject]) -> None:
    if not objects:
        print("No local durable data files were found.")
        return
    for item in objects:
        row_text = "" if item.row_count is None else f" rows={item.row_count}"
        print(
            f"{item.source_label} -> {item.destination} "
            f"bytes={len(item.content)}{row_text} sha256={item.sha256}"
        )


def apply_migration(
    objects: list[MigrationObject],
    *,
    replace_existing: bool,
) -> None:
    """Upload changed objects atomically and verify every resulting object."""
    require_private_data_store()
    changed: dict[str, bytes] = {}
    for item in objects:
        remote = read_private_data_file(item.destination)
        if remote is None:
            changed[item.destination] = item.content
            continue
        remote_hash = hashlib.sha256(remote.content).hexdigest()
        if remote_hash == item.sha256:
            continue
        if not replace_existing:
            raise RuntimeError(
                "remote destination already contains different bytes; "
                f"review before using --replace-existing: {item.destination}"
            )
        changed[item.destination] = item.content

    if changed:
        write_private_data_files_atomic(
            changed,
            "Migrate local durable application data",
        )

    for item in objects:
        verified = read_private_data_file(item.destination, required=True)
        if verified is None:  # pragma: no cover - required=True raises first.
            raise RuntimeError(f"verification read failed: {item.destination}")
        verified_hash = hashlib.sha256(verified.content).hexdigest()
        if verified_hash != item.sha256:
            raise RuntimeError(f"verification hash mismatch: {item.destination}")
        print(
            f"VERIFIED {private_data_display_path(item.destination)} "
            f"bytes={len(verified.content)} sha256={verified_hash}"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="upload and verify; without this flag the command is a dry run",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="allow replacement when a remote destination has different bytes",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.replace_existing and not args.apply:
        raise SystemExit("--replace-existing requires --apply")
    objects = discover_objects()
    _print_plan(objects)
    if not args.apply:
        print("DRY RUN: no remote or local files were changed.")
        return 0
    apply_migration(objects, replace_existing=bool(args.replace_existing))
    print("Migration verification complete. Local source files were retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
