from dataclasses import replace
from contextlib import nullcontext
from hashlib import sha256
import json
import stat
import struct
import sys
import zipfile

import pytest

from practice_engine.data.release_archive import DIRECTORIES, Limits, MEMBERS, PROFILE, inspect_archive, main


def make_archive(path, *, names=None, compression=zipfile.ZIP_STORED, symlink=False, payload=None):
    names = sorted(MEMBERS) if names is None else names
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for index, name in enumerate(names):
            data = payload if payload is not None else b"Original synthetic fixture, not student data: " + name.encode()
            if symlink and index == 0:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(info, data)
            else:
                archive.writestr(name, data)
    return path


def test_receipt_hashes_bytes_without_parsing_or_extracting(tmp_path):
    path = make_archive(tmp_path / "synthetic.zip")
    result = inspect_archive(path, profile=PROFILE)
    assert result["sha256"] == sha256(path.read_bytes()).hexdigest()
    assert result["bytes"] == path.stat().st_size
    assert result["zip_integrity_valid"] is True
    assert {row["name"] for row in result["members"]} == MEMBERS
    with zipfile.ZipFile(path) as archive:
        for row in result["members"]:
            data = archive.read(row["name"])
            assert row["bytes"] == len(data) and row["sha256"] == sha256(data).hexdigest()
    assert "Original synthetic" not in json.dumps(result)
    assert set(result) == {"receipt_version", "profile", "bytes", "sha256", "zip_integrity_valid", "members"}
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("name", ["../escape.csv", "/absolute.csv", "C:/drive.csv", "Data/./MainTable.csv"])
def test_unsafe_member_path_rejected(tmp_path, name):
    path = make_archive(tmp_path / "bad.zip", names=[name, *sorted(MEMBERS)[1:]])
    with pytest.raises(ValueError):
        inspect_archive(path, profile=PROFILE)


@pytest.mark.parametrize("duplicate", ["Data/MainTable.csv", "DATA/MAINTABLE.CSV"])
def test_duplicate_case_alias_rejected(tmp_path, duplicate):
    with pytest.warns(UserWarning) if duplicate == "Data/MainTable.csv" else nullcontext():
        path = make_archive(tmp_path / "bad.zip", names=[*sorted(MEMBERS), duplicate])
    with pytest.raises(ValueError, match="Duplicate"):
        inspect_archive(path, profile=PROFILE)


def test_raw_backslash_member_rejected(tmp_path):
    path = make_archive(tmp_path / "bad.zip")
    path.write_bytes(path.read_bytes().replace(b"Data/MainTable.csv", b"Data\\MainTable.csv"))
    with pytest.raises(ValueError, match="Unsafe"):
        inspect_archive(path, profile=PROFILE)


def test_only_known_empty_directory_markers_allowed(tmp_path):
    path = make_archive(tmp_path / "synthetic.zip", names=[*sorted(MEMBERS), *sorted(DIRECTORIES)], payload=b"")
    result = inspect_archive(path, profile=PROFILE)
    assert {row["name"] for row in result["members"]} == MEMBERS | DIRECTORIES
    for names, payload in (([*sorted(MEMBERS), "unexpected/"], b""),
                           ([*sorted(MEMBERS), "Data/"], b"not empty")):
        path = make_archive(path, names=names, payload=payload)
        with pytest.raises(ValueError, match="directory marker"):
            inspect_archive(path, profile=PROFILE)


def test_symlink_unknown_profile_and_missing_member_rejected(tmp_path):
    path = make_archive(tmp_path / "bad.zip", symlink=True)
    with pytest.raises(ValueError, match="Unsafe"):
        inspect_archive(path, profile=PROFILE)
    with pytest.raises(ValueError, match="Unknown"):
        inspect_archive(path, profile="different-release")
    path = make_archive(path, names=sorted(MEMBERS)[:-1])
    with pytest.raises(ValueError, match="selected release profile"):
        inspect_archive(path, profile=PROFILE)


def test_bounds_and_high_compression_fail_closed(tmp_path):
    path = make_archive(tmp_path / "synthetic.zip")
    for limits in (replace(Limits(), archive_bytes=path.stat().st_size - 1),
                   replace(Limits(), members=5), replace(Limits(), member_bytes=1),
                   replace(Limits(), expanded_bytes=1)):
        with pytest.raises(ValueError):
            inspect_archive(path, profile=PROFILE, limits=limits)
    path = make_archive(path, compression=zipfile.ZIP_DEFLATED, payload=b"synthetic" * 10000)
    with pytest.raises(ValueError, match="expansion"):
        inspect_archive(path, profile=PROFILE)
    with pytest.raises(ValueError):
        Limits(compression_ratio=True)


def test_corruption_and_truncation_rejected(tmp_path):
    path = make_archive(tmp_path / "synthetic.zip")
    data = path.read_bytes()
    marker = data.index(b"Original synthetic")
    path.write_bytes(data[:marker] + b"X" + data[marker + 1:])
    with pytest.raises(zipfile.BadZipFile, match="CRC"):
        inspect_archive(path, profile=PROFILE)
    path.write_bytes(data[:-10])
    with pytest.raises(ValueError):
        inspect_archive(path, profile=PROFILE)


def test_forged_directory_count_rejected_before_zipfile_allocation(tmp_path, monkeypatch):
    path = make_archive(tmp_path / "synthetic.zip")
    data = bytearray(path.read_bytes())
    end = data.rfind(b"PK\x05\x06")
    struct.pack_into("<2H", data, end + 8, 1, 1)
    path.write_bytes(data)
    monkeypatch.setattr(zipfile, "ZipFile", lambda *_: pytest.fail("must preflight before allocation"))
    with pytest.raises(ValueError, match="count mismatch"):
        inspect_archive(path, profile=PROFILE)


@pytest.mark.parametrize("flag,method", [(1, zipfile.ZIP_STORED), (0, zipfile.ZIP_BZIP2)])
def test_encrypted_or_unsupported_compression_rejected(tmp_path, flag, method):
    path = make_archive(tmp_path / "synthetic.zip")
    data = bytearray(path.read_bytes())
    central = data.index(b"PK\x01\x02")
    struct.pack_into("<2H", data, central + 8, flag, method)
    path.write_bytes(data)
    with pytest.raises(ValueError, match="Unsafe"):
        inspect_archive(path, profile=PROFILE)


def test_mutation_during_member_reads_rejected(tmp_path, monkeypatch):
    path = make_archive(tmp_path / "synthetic.zip")
    original = zipfile.ZipFile.open
    def mutate(self, *args, **kwargs):
        with path.open("ab") as stream:
            stream.write(b"changed")
        return original(self, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "open", mutate)
    with pytest.raises(ValueError, match="changed"):
        inspect_archive(path, profile=PROFILE)


def test_cli_reports_only_complete_integrity_and_hides_failure_paths(tmp_path, monkeypatch, capsys):
    path = make_archive(tmp_path / "synthetic.zip")
    monkeypatch.setattr(sys, "argv", ["release_archive", str(path), "--profile", PROFILE])
    main()
    assert json.loads(capsys.readouterr().out)["sha256"] == sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(sys, "argv", ["release_archive", str(tmp_path / "private-path-not-exposed"), "--profile", PROFILE])
    with pytest.raises(SystemExit) as error:
        main()
    output = capsys.readouterr()
    assert error.value.code == 2 and output.out == ""
    assert "private-path-not-exposed" not in output.err and "Traceback" not in output.err
    path = make_archive(tmp_path / "private-path-not-exposed.zip", compression=zipfile.ZIP_DEFLATED)
    data = bytearray(path.read_bytes())
    name_size, extra_size = struct.unpack_from("<2H", data, 26)
    data[30 + name_size + extra_size] = 7  # Reserved DEFLATE block type.
    path.write_bytes(data)
    monkeypatch.setattr(sys, "argv", ["release_archive", str(path), "--profile", PROFILE])
    with pytest.raises(SystemExit):
        main()
    output = capsys.readouterr()
    assert output.out == "" and "private-path-not-exposed" not in output.err and "Traceback" not in output.err
