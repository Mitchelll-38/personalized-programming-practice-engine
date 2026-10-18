# Frozen embedding cache boundary

Owner: model platform engineer. Purpose: cache caller-provided vectors under exact
content and pinned encoder declarations, before an encoder integration exists.
Acceptance: role/content/config invalidation, finite dimension-matched vectors,
strict detached metadata, corruption detection and atomic new-file publication.
Dependencies: no neural runtime or encoder download. This PR contains no encoder
execution, content LSTM, API activation or real-data processing. The coordinator
owns chronological progress records.

Plan: define immutable encoder declarations and cache entries; derive content and
entry keys from exact UTF-8 input plus role/config; validate checksums on write/read;
publish a new cache file without replacing an existing entry. Test every key input,
vector/schema corruption, detached serialization and failed publication cleanup.

Only original synthetic texts and manually supplied synthetic vectors are used in
tests. Naming an encoder does not claim those vectors came from that encoder.

`EncoderConfig` records encoder repository and full 40-character commit revision,
tokenizer repository/revision, pooling (`mean` or `cls`), maximum token count,
truncation direction and vector dimension. Revisions are declarations; this module
does not fetch or authenticate model/tokenizer files. A future encoder integration
must define its exact pooling/tokenization behavior and version any policy changes.

`save_embedding(path, content, role, config, vector)` stores one immutable entry.
The key includes the cache format version, SHA-256 of exact UTF-8 content, role
(`problem-text` or `historical-code`) and every encoder field. Whitespace and Unicode
normalization differences intentionally change the key. Candidate submitted code
has no allowed role. The caller remains responsible for causal history ownership;
a historical-code role alone cannot establish that a submission precedes a target.

`load_embedding(path, content, role, config)` revalidates strict metadata, key,
vector dimension/finite values and entry checksum, then matches the requested key.
Vectors are immutable tuples; `to_dict()` returns detached JSON values. Duplicate
keys and extra fields are rejected. Checksums detect accidental alteration but
do not authenticate a producer: someone can recompute hashes over arbitrary vectors.
`vector_origin=caller-provided` makes no assertion that an encoder executed.

Files contain configuration, hashes and vectors, never input text or submitted
code. Hashes and vectors can still reveal information about their source and must
be treated as private derived data. Keep project caches inside ignored
`.data/private/data/embedding-cache/`, after the existing release/usage gate is
satisfied for real input. Do not commit real cache entries to public git.

Publication writes and fsyncs a temporary sibling file, then uses an atomic
same-filesystem hard link that fails if the destination already exists, including
concurrent writers. Temporary files are removed on normal success/failure. The
filesystem must support hard links; unsupported filesystems fail without replacing
the destination. Abrupt termination can leave a private temporary file. No fallback
to an overwriting rename exists. A directory-level cache/index, encoder runtime,
batch tokenization and content-model training are separate PRs.
