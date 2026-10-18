# Official S19 release acquisition

Owner: coordinator/data lead. Purpose: replace failed-download status with a
verified private archive and structural receipt. Acceptance: official identity,
nonzero size/checksum, complete ZIP verification, safe contained extraction,
current usage observations and explicit remaining import gates. Dependency:
user-authenticated DataShop. Acquisition does not enable training or publish data.

Plan for this record: verify the browser-produced file, hash archive members,
reject unsafe paths/symlinks before extraction, and inspect structural information.
Keep acquired data/audits private; obtain independent compatibility/provenance review
before proposing importer or training changes.

## Acquisition evidence — October 18, 2026

The authenticated browser downloaded file ID **27181** from the official
[dataset 3458 listing](https://pslcdatashop.web.cmu.edu/Files?datasetId=3458),
titled **2nd CSEDM Data Challenge - S19 All Data v1.0**:

- Filename: `S19_All_Release_2_10_22.zip`, posted February 10, 2022.
- Size: **7,927,271 bytes**.
- SHA-256: `c0c21654766c05da4f1beb691ca152181e3b08679855dc70ea7cea01a500cec1`.
- All nine members passed ZIP CRC verification; no unsafe path or symbolic link
  was accepted. Six members are CSV files.
- Storage: `.data/private/data/releases/codeworkout-s19-2022-02-10/`, containing
  the archive, `extracted/` and `acquisition-structural-receipt.json` with member
  hashes. The verified new browser download was relocated from Downloads.

The release description includes Spring 2019 training/testing labels and describes
the test data as the challenge's practice phase. `early.csv` and `late.csv` are not
this project's frozen partitions. No challenge-label training/evaluation workflow
has been run, and no Fall 2019 source was mixed into this release.

## Current usage observations

The dataset's **Terms of Use** tab reports no additional project terms and points
to [DataShop's terms](https://pslcdatashop.web.cmu.edu/Terms). Those terms restrict
use to noncommercial research, prohibit de-anonymization and redistribution, and
require collaborators needing data access to establish their own accounts and
agree to the terms. The public code repository grants no dataset rights. Research
access and redistribution permission are separate; acquisition does not authorize
public data/model publication. No new agreement was submitted during inspection.
Archives, submitted code, student identifiers, grades, derived rows and any acquired
catalog stay private. No account email, credential or session material is published.

## Structural boundary and unresolved compatibility

The archive contains `Data/MainTable.csv`, `Data/CodeStates/CodeStates.csv`,
`Data/DatasetMetadata.csv`, `Data/LinkTables/Subject.csv`, `early.csv` and `late.csv`.
There is no separate statement/concept catalog in that inventory. The subject
link table includes a course-grade field outside this project's prediction inputs;
it has not been used for modeling. Current code expects the extracted `Data/`
directory, rather than its parent, as the format-adapter input.

Dataset metadata declares ProgSnap version 6, consistent event ordering with a
restricted scope of `SubjectID;AssignmentID;ProblemID`, and table-based code
states. That scope does not establish a total cross-problem learner timeline.
An independent local structural audit found naive timestamps, both `UTC` and `0`
timezone representations, scored-run timestamp ties and disagreements between
restricted `Order` and timestamp chronology. Actual field interpretation and an
explicit ambiguity policy need review; file position or IDs cannot invent order.
The aggregate audit and its script remain in the private release directory.

The format adapter, manifest and training gates remain unchanged. Acquisition is
complete; authorized statement/concept coverage, grading interpretation,
time/order policy, compatibility and reviewed real-source provenance remain
separate acceptance gates. No canonical real-data import or training has run.
