# Bounded S19 archive inspection

Owner: product/platform engineer. Purpose: reproduce archive integrity checks
without importing records, extracting files or granting research/publication rights.
Acceptance: explicit known six-member S19-full profile; bounded ZIP/CRC/SHA256
verification; unsafe/duplicate/symlink/encrypted/unsupported members rejected;
aggregate receipt only; original synthetic ZIP regressions and private official
archive smoke. Dependencies: release acquisition receipt and documented format.

Plan before implementation: standard-library inspector and module CLI, fixed known
member set, preflight central-directory limits, streaming hash/CRC reads and clear
private errors. No CSV parsing, extraction, canonical import or training activation.
Exact source identity does not establish authorization, catalog/grading/time
verification or permission to redistribute downloaded data.

## Usage and boundaries

```powershell
$env:PYTHONPATH = 'src'
python -m practice_engine.data.release_archive <private-archive.zip> --profile codeworkout-s19-full-2022-02-10
```

The CLI emits a complete JSON integrity receipt on stdout only after all checks
pass. Save it under ignored project-private storage when inspecting private data.
Failures return a generic error without exception details or private paths. The
library API `inspect_archive(Path(...), profile=PROFILE)` returns the same receipt.
It performs no CSV parsing, row counting, extraction, candidate conversion or
source-provenance verification. Downloaded bytes remain private.

The explicit profile requires the six known CSV paths and permits only the three
known empty directory markers (`Data/`, `Data/CodeStates/`, `Data/LinkTables/`).
Markers must have zero compressed/uncompressed size and CRC; all present members are hashed. Additional,
missing, duplicate/case-alias or unsafe names fail. Symlinks/nonregular files,
encryption and compression other than stored/DEFLATE fail. This is a narrow
profile rather than a general archive browser; ZIP64 end directories and multipart archives are rejected.

Default limits are 64 MiB archive, 64 entries, 128 MiB per member, 256 MiB expanded
and 100:1 per-member expansion ratio. Directory records are preflighted before
ZipFile allocates entry objects; byte counts are enforced while streaming. Member
reads check CRC. Archive bytes are hashed before and after member reads to reject
concurrent changes. These integrity checks do not authenticate origin or authorize
research use, catalog publication, grading/time reconstruction or real training.

## Verification record

Original synthetic ZIP fixtures exercise valid arbitrary bytes, unsafe paths,
case/duplicate aliases, symlinks, directory markers, missing/unknown profiles,
resource bounds, CRC/truncation/DEFLATE failures, forged directory counts and
concurrent mutation. No downloaded data is a committed fixture.

On client date 2026-10-18, the private official S19 archive smoke passed at
7,927,271 bytes with SHA-256
`c0c21654766c05da4f1beb691ca152181e3b08679855dc70ea7cea01a500cec1`.
The six file hashes exactly matched the acquisition receipt; three empty directory
markers were also verified. The resulting integrity receipt stays private. This
is an archive check, not an import or empirical result.

The focused archive/import/CLI/family/manifest regression run passed 52 tests
in 9.91 seconds. All new fixtures are generated from original synthetic bytes.
