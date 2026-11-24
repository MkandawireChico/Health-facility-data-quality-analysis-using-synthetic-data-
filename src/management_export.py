"""Portable ZIP export for the expanded synthetic facility management review."""
from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any

import pandas as pd


def build_management_review_archive(
    tables: dict[str, pd.DataFrame], summary: dict[str, Any]
) -> bytes:
    """Build a deterministic, in-memory ZIP containing a JSON summary and CSV tables."""
    if not isinstance(tables, dict) or not isinstance(summary, dict):
        raise ValueError("Management export requires table and summary dictionaries")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("management_summary.json", json.dumps(summary, indent=2, default=str))
        for filename, frame in sorted(tables.items()):
            if (
                not isinstance(filename, str)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.csv", filename)
                or filename in {"management_summary.csv"}
            ):
                raise ValueError(f"Invalid management export filename: {filename!r}")
            if not isinstance(frame, pd.DataFrame):
                raise ValueError(f"Management export table must be a DataFrame: {filename}")
            archive.writestr(filename, frame.to_csv(index=False))
    return buffer.getvalue()
