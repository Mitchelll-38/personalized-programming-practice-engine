from hashlib import sha1, sha256
import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")

from practice_engine.data.schema import Candidate, Interaction
from practice_engine.models import codebert
from practice_engine.models.embedding_cache import cache_key, save_embedding
from practice_engine.models.serving import PredictionInput


@pytest.fixture
def query():
    prior = Interaction(student_id="synthetic", problem_id="prior", sequence_index=0,
                        problem_text="Prior", concept_ids=("loops",), correct=False,
                        attempt_number=1, submitted_code="return 17;")
    return PredictionInput(student_id="synthetic", target_sequence_index=1, history=(prior,),
        candidate=Candidate(problem_id="candidate", problem_text="Candidate", concept_ids=("loops",)))


@pytest.fixture
def backend(tmp_path, monkeypatch):
    directory = tmp_path.resolve()
    monkeypatch.setenv("HF_HOME", str(directory / "huggingface"))
    monkeypatch.setenv("HF_XET_CACHE", str(directory / "huggingface/xet"))
    monkeypatch.setitem(sys.modules, "huggingface_hub.constants", SimpleNamespace(
        HF_HOME=str(directory / "huggingface"), HF_XET_CACHE=str(directory / "huggingface/xet")))
    state = SimpleNamespace(calls=[], model_kwargs=None, tokenizer_kwargs=None, nan=False, empty_mask=False)
    class Tokenizer:
        def __call__(self, texts, **kwargs):
            state.calls.append((texts, kwargs))
            rows = [{"Prior": [1, 3, 5], "Candidate": [1, 3], "return 17;": [1, 7, 9]}[text]
                    [:kwargs["max_length"]] for text in texts]
            width = max(map(len, rows))
            return {"input_ids": torch.tensor([row + [1000] * (width - len(row)) for row in rows]),
                    "attention_mask": torch.tensor([[0 if state.empty_mask else 1] * len(row)
                                                     + [0] * (width - len(row)) for row in rows])}
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.parameter = torch.nn.Parameter(torch.zeros(1))
            self.config = SimpleNamespace(hidden_size=768, max_position_embeddings=514)
        def forward(self, input_ids, attention_mask):
            assert not self.training and not torch.is_grad_enabled() and not self.parameter.requires_grad
            hidden = input_ids.float().unsqueeze(-1).repeat(1, 1, 768)
            if state.nan:
                hidden[:] = float("nan")
            return SimpleNamespace(last_hidden_state=hidden)
    def tokenizer_factory(path, **kwargs):
        state.tokenizer_kwargs = kwargs
        return Tokenizer()
    def model_factory(path, **kwargs):
        state.model_kwargs = kwargs
        state.model = Model()
        return state.model
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(
        AutoTokenizer=SimpleNamespace(from_pretrained=tokenizer_factory),
        RobertaModel=SimpleNamespace(from_pretrained=model_factory)))
    monkeypatch.setattr(codebert, "_assets", lambda directory, allow_download: directory)
    state.directory = directory
    return state


def test_masked_mean_cache_reuse_and_declared_safe_loading(backend, query):
    encoder = codebert.FrozenCodeBERT(backend.directory)
    key = cache_key(query.candidate.problem_text, "problem-text", encoder.config)
    save_embedding(backend.directory / "embeddings" / f"{key}.json", query.candidate.problem_text,
                   "problem-text", encoder.config, [99.] * 768)  # Earlier manually provided fixture.
    entries = encoder.encode(query)
    assert [entry.role for entry in entries] == ["problem-text", "historical-code", "problem-text"]
    assert [entry.vector[0] for entry in entries] == pytest.approx([3., 17 / 3, 2.])
    assert backend.model_kwargs == dict(local_files_only=True, trust_remote_code=False,
        weights_only=True, use_safetensors=False, dtype=torch.float32)
    assert backend.tokenizer_kwargs == dict(local_files_only=True, trust_remote_code=False, use_fast=True)
    assert backend.calls[0][1] == dict(padding=True, truncation=True, max_length=512,
        add_special_tokens=True, return_attention_mask=True, return_tensors="pt")
    assert encoder.encode(query) == entries and len(backend.calls) == 1
    cached = backend.directory / "embeddings" / codebert.CACHE_NAMESPACE
    assert all("return 17" not in path.read_text() for path in cached.glob("*.json"))
    other = codebert.FrozenCodeBERT(backend.directory, config=codebert.codebert_config(pooling="cls", max_tokens=2, truncation="left"))
    assert all(entry.vector[0] == 1 for entry in other.encode(query))
    assert len(list(cached.glob("*.json"))) == 6
    assert other._tokenizer.truncation_side == "left"


def test_causal_query_revalidation_excludes_target_responses(backend, query):
    encoder = codebert.FrozenCodeBERT(backend.directory)
    assert [item.text for item in codebert.query_contents(query)] == ["Prior", "return 17;", "Candidate"]
    for change in ({"sequence_index": 1}, {"student_id": "other"}, {"attempt_number": 2}, {"problem_id": "candidate"}):
        invalid = query.model_copy(update={"history": (query.history[0].model_copy(update=change),)})
        with pytest.raises(ValueError):
            encoder.encode(invalid)
    with pytest.raises(ValueError, match="label-free"):
        codebert.query_contents({**query.model_dump(), "label": True})
    blank = query.model_copy(update={"history": (query.history[0].model_copy(update={"submitted_code": " "}),)})
    assert [item.text for item in codebert.query_contents(blank)] == ["Prior", "Candidate"]
    assert not backend.calls and not (backend.directory / "embeddings").exists()


def test_corruption_and_invalid_backend_outputs_never_publish(backend, query):
    encoder = codebert.FrozenCodeBERT(backend.directory)
    backend.empty_mask = True
    with pytest.raises(ValueError, match="attention"):
        encoder.encode(query)
    backend.empty_mask, backend.nan = False, True
    with pytest.raises(ValueError, match="nonfinite"):
        encoder.encode(query)
    assert not (backend.directory / "embeddings").exists()
    backend.nan = False
    encoder.encode(query)
    path = next((backend.directory / "embeddings" / codebert.CACHE_NAMESPACE).glob("*.json"))
    value = json.loads(path.read_text())
    value["vector"][0] = 99.
    path.write_text(json.dumps(value))
    before = len(backend.calls)
    with pytest.raises(ValueError):
        encoder.encode(query)
    assert len(backend.calls) == before


@pytest.mark.parametrize("config", [codebert.codebert_config(max_tokens=513), codebert.codebert_config(max_tokens=1),
    codebert.codebert_config().model_copy(update={"revision": "a" * 40})])
def test_unverified_snapshot_and_bad_token_limits_rejected_before_loading(backend, config):
    with pytest.raises(ValueError, match="verified"):
        codebert.FrozenCodeBERT(backend.directory, config=config)


def test_environment_and_already_imported_hub_mismatch_rejected(backend, monkeypatch):
    monkeypatch.delenv("HF_XET_CACHE")
    with pytest.raises(ValueError, match="HF_XET_CACHE"):
        codebert.FrozenCodeBERT(backend.directory)
    monkeypatch.setenv("HF_XET_CACHE", str(backend.directory / "huggingface/xet"))
    monkeypatch.setitem(sys.modules, "huggingface_hub.constants", SimpleNamespace(HF_HOME="elsewhere", HF_XET_CACHE="elsewhere"))
    with pytest.raises(ValueError, match="fresh configured process"):
        codebert.FrozenCodeBERT(backend.directory)


def test_official_asset_flags_hashes_and_revision(tmp_path, monkeypatch):
    # Tiny original synthetic bytes replace official metadata, never actual weights.
    blobs = {"config.json": b"{}", "vocab.json": b"synthetic vocabulary"}
    for name, content in {**blobs, "pytorch_model.bin": b"synthetic weights"}.items():
        (tmp_path / name).write_bytes(content)
    monkeypatch.setattr(codebert, "BLOBS", {name: sha1(f"blob {len(content)}\0".encode() + content).hexdigest()
                                          for name, content in blobs.items()})
    monkeypatch.setattr(codebert, "WEIGHTS_SHA256", sha256(b"synthetic weights").hexdigest())
    calls = []
    def download(repository, filename, **kwargs):
        calls.append(kwargs)
        assert repository == codebert.REPOSITORY
        return str(tmp_path / filename)
    monkeypatch.setitem(sys.modules, "huggingface_hub", SimpleNamespace(hf_hub_download=download))
    assert codebert._assets(tmp_path, False) == tmp_path
    assert all(call == dict(revision=codebert.REVISION, cache_dir=str(tmp_path / "huggingface/hub"),
                            local_files_only=True, token=False) for call in calls)
    calls.clear()
    codebert._assets(tmp_path, True)
    assert all(call["local_files_only"] is False and call["token"] is False for call in calls)
    alternate = tmp_path / "tokenizer.json"
    alternate.write_text(json.dumps({"version": "1.0", "model": {"type": "BPE", "vocab": {"synthetic": 0}, "merges": []}}))
    with pytest.raises(ValueError, match="Unexpected encoder snapshot"):
        codebert._assets(tmp_path, False)
    alternate.unlink()
    (tmp_path / "pytorch_model.bin").write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        codebert._assets(tmp_path, False)


def test_module_import_does_not_load_optional_backends():
    subprocess.run([sys.executable, "-c", "import sys; import practice_engine.models.codebert; "
        "assert not {'torch','transformers','huggingface_hub'}.intersection(sys.modules)"], check=True)
