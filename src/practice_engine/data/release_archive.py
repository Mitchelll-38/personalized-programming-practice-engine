"""Bounded integrity inspection of a known archive shape; never import or extract."""

import argparse
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile
import zlib

PROFILE = "codeworkout-s19-full-2022-02-10"
MEMBERS = frozenset({"Data/MainTable.csv", "Data/DatasetMetadata.csv",
    "Data/CodeStates/CodeStates.csv", "Data/LinkTables/Subject.csv", "early.csv", "late.csv"})
DIRECTORIES = frozenset({"Data/", "Data/CodeStates/", "Data/LinkTables/"})
CHUNK = 64 * 1024


@dataclass(frozen=True)
class Limits:
    archive_bytes: int = 64 * 1024 * 1024
    member_bytes: int = 128 * 1024 * 1024
    expanded_bytes: int = 256 * 1024 * 1024
    members: int = 64
    compression_ratio: int = 100

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in vars(self).values()):
            raise ValueError("Archive limits must be positive integers")


def _directory_preflight(stream, size, limits):
    # Bound directory allocation before ZipFile creates one object per member.
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    position = tail.rfind(b"PK\x05\x06")
    if position < 0 or len(tail) - position < 22:
        raise ValueError("Missing ZIP directory")
    _, disk, directory_disk, disk_entries, entries, directory_size, offset, comment = struct.unpack(
        "<4s4H2LH", tail[position:position + 22])
    absolute = size - len(tail) + position
    if (disk or directory_disk or disk_entries != entries or entries > limits.members
            or entries == 65535 or offset == 0xffffffff or directory_size == 0xffffffff
            or directory_size > limits.members * (46 + 65535 * 3)
            or offset + directory_size != absolute or position + 22 + comment != len(tail)):
        raise ValueError("Unsupported or oversized ZIP directory")
    stream.seek(offset)
    for _ in range(entries):
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise ValueError("Invalid ZIP directory entry")
        variable_bytes = sum(struct.unpack("<3H", header[28:34]))
        stream.seek(variable_bytes, 1)
        if stream.tell() > offset + directory_size:
            raise ValueError("Invalid ZIP directory extent")
    if stream.tell() != offset + directory_size:
        raise ValueError("ZIP directory entry count mismatch")


def inspect_archive(path: Path, *, profile: str, limits: Limits = Limits()) -> dict:
    """Return aggregate hashes only. This profile identifies shape, not provenance."""
    if profile != PROFILE:
        raise ValueError("Unknown release archive profile")
    with path.open("rb") as stream:
        stream.seek(0, 2)
        size = stream.tell()
        if not 0 < size <= limits.archive_bytes:
            raise ValueError("Archive byte limit exceeded")
        _directory_preflight(stream, size, limits)
        stream.seek(0)
        archive_hash = sha256()
        hashed = 0
        while chunk := stream.read(CHUNK):
            hashed += len(chunk)
            if hashed > limits.archive_bytes:
                raise ValueError("Archive byte limit exceeded")
            archive_hash.update(chunk)
        if hashed != size:
            raise ValueError("Archive changed during inspection")
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if len(names) > limits.members or len(names) != len(set(name.casefold() for name in names)):
                raise ValueError("Duplicate or excessive ZIP members")
            declared = 0
            for entry in entries:
                name = entry.filename
                directory = entry.is_dir()
                parts = PurePosixPath(name).parts
                canonical_name = "/".join(parts) + ("/" if directory else "")
                mode = entry.external_attr >> 16
                if (not parts or name != entry.orig_filename or name != canonical_name or "\\" in name or ":" in name
                        or name.startswith("/") or ".." in parts
                        or stat.S_IFMT(mode) not in (0, stat.S_IFDIR if directory else stat.S_IFREG)
                        or (not directory and entry.external_attr & 0x10)
                        or entry.flag_bits & 1 or entry.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)):
                    raise ValueError("Unsafe or unsupported ZIP member")
                if directory and (name not in DIRECTORIES or entry.file_size or entry.compress_size or entry.CRC):
                    raise ValueError("Unexpected ZIP directory marker")
                declared += entry.file_size
                if (entry.file_size > limits.member_bytes or declared > limits.expanded_bytes
                        or entry.file_size > max(1, entry.compress_size) * limits.compression_ratio):
                    raise ValueError("ZIP expansion limit exceeded")
            if set(names) - DIRECTORIES != MEMBERS:
                raise ValueError("Archive does not match the selected release profile")
            receipt = []
            expanded = 0
            for entry in sorted(entries, key=lambda item: item.filename):
                digest = sha256()
                count = 0
                with archive.open(entry) as member:
                    while chunk := member.read(CHUNK):
                        count += len(chunk)
                        expanded += len(chunk)
                        if count > limits.member_bytes or expanded > limits.expanded_bytes:
                            raise ValueError("ZIP expansion limit exceeded")
                        digest.update(chunk)
                if count != entry.file_size:
                    raise ValueError("ZIP member size mismatch")
                receipt.append({"name": entry.filename, "bytes": count, "sha256": digest.hexdigest()})
        # Compare the same open file again: do not associate member hashes with
        # archive bytes modified while hashing/decompressing it.
        stream.seek(0)
        final_hash = sha256()
        final_size = 0
        while chunk := stream.read(CHUNK):
            final_size += len(chunk)
            if final_size > limits.archive_bytes:
                raise ValueError("Archive byte limit exceeded")
            final_hash.update(chunk)
        if final_size != size or final_hash.digest() != archive_hash.digest():
            raise ValueError("Archive changed during inspection")
    return {"receipt_version": "release-archive-integrity-v1", "profile": profile,
            "bytes": size, "sha256": archive_hash.hexdigest(), "zip_integrity_valid": True,
            "members": receipt}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--profile", choices=(PROFILE,), required=True)
    args = parser.parse_args()
    try:
        result = inspect_archive(args.archive, profile=args.profile)
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, zlib.error):
        parser.error("Archive inspection failed; check the private archive, profile and bounds.")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
