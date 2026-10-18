# Optional encoder environment

Owner: model platform engineer. Purpose: pin an optional local Transformers CPU
backend before the separate frozen extraction adapter. Acceptance: compatible
pinned dependencies, offline backend import, generic imports remain lazy and CI
never fetches model weights. Dependencies: pinned CPU Torch environment and the
existing exact-content embedding cache. No encoder execution is added here.

Plan: resolve Transformers against the existing research/dev/CPU pins; install and
check imports locally; extend the dedicated CPU CI backend check with offline Hub
settings. Record model-source observations without claiming a weight-license field
exists. Adapter code, actual model download and synthetic encoding smoke follow
in separate work; real student-data acquisition remains a different gate.

## Setup and verification

From the main project root, use the shared virtual environment and contained caches:

```powershell
$env:PIP_CACHE_DIR = Join-Path (Get-Location) '.data/private/data/package-cache'
$env:HF_HOME = Join-Path (Get-Location) '.data/private/data/encoders/huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock -r requirements-neural.lock -r requirements-encoder.lock
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -c "from transformers import AutoTokenizer, RobertaModel; import tokenizers, safetensors"
```

The optional `encoder` extra declares Torch/Transformers compatibility. The lock
pins the resolved backend and its additional dependencies against the existing
CPU/research/dev locks; it does not replace those locks or install model weights.
Transformers 5.20.1 is the inspected stable [PyPI release](https://pypi.org/project/transformers/5.20.1/),
not a development checkout. Its required Hub/tokenizer/safetensors ranges are
resolved in the companion lock. The dedicated CPU CI job performs backend imports
with Hub networking disabled, then runs the suite. Ordinary API installation and
generic baseline imports remain independent of this optional stack.

## Official model observations — October 17, 2026

The [Microsoft project](https://github.com/microsoft/CodeBERT) documents RoBERTa
tokenization/model loading and contextual embeddings. Its [source license](https://github.com/microsoft/CodeBERT/blob/master/LICENSE)
is MIT. The [official model API](https://huggingface.co/api/models/microsoft/codebert-base)
identifies public, ungated `microsoft/codebert-base` revision
`3b0952feddeffad0063f274080e3c23d75e7eb39`. The [revision file listing](https://huggingface.co/microsoft/codebert-base/tree/3b0952feddeffad0063f274080e3c23d75e7eb39)
contains tokenizer/config files and approximately 499 MB `pytorch_model.bin`, with
no safetensors checkpoint or separate LICENSE file. The model card/API does not
declare a checkpoint-specific license field. The project source MIT observation
is not an independently verified checkpoint license; do not describe it as one.

The [pinned config](https://huggingface.co/microsoft/codebert-base/blob/3b0952feddeffad0063f274080e3c23d75e7eb39/config.json)
declares hidden size 768 and 514 position embeddings with padding ID 1. Extraction
must respect the 512-token total limit, including beginning/end special tokens.
The [pinned file metadata](https://huggingface.co/api/models/microsoft/codebert-base/revision/3b0952feddeffad0063f274080e3c23d75e7eb39?blobs=true)
reports the PyTorch file size as 498627950 bytes and LFS SHA-256
`28b61fd8fa069f6bc966f4cb9572a4026ab2a784fca8fb224020d91b744e32d6`.
These are remote metadata observations, not a receipt for downloaded local bytes.

No model weights are downloaded by this change, no remote inference service is
used and no student inputs are sent anywhere. A later local adapter must pin the
revision, retain license/source observations, use explicit private cache paths,
disable remote code, keep weights-only deserialization enabled and declare exact
tokenization/truncation/pooling. Any actual-weight smoke must use original
synthetic content and record software behavior separately from predictive results.
