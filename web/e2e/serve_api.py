"""Serve the real demo API against a unique temporary database, never user data."""

import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
with TemporaryDirectory(prefix="practice-smoke-") as directory:
    os.environ["PRACTICE_DB_PATH"] = str(Path(directory) / "replay.sqlite3")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8001)
