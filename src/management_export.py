"""Portable ZIP export for the expanded synthetic facility management review."""
from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Any

import pandas as pd


_RESERVED_ARCHIVE_NAMES = {"management_summary.json", "management_summary.csv"}
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _spreadsheet_safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Escape formula-like text cells without changing numeric values."""
    safe = frame.copy()
    for column in safe.columns:
        if pd.api.types.is_object_dtype(safe[column].dtype) or pd.api.types.is_string_dtype(
            safe[column].dtype
        ):
            def escape_text(value: Any) -> Any:
                if not isinstance(value, str):
                    return value
                probe = value.lstrip(" \t\r\n\v\f\x00")
                if probe.startswith(_FORMULA_PREFIXES):
                    return "'" + value
                return value

            safe[column] = safe[column].map(escape_text)
    return safe


def _archive_info(filename: str) -> zipfile.ZipInfo:
    """Use a fixed ZIP timestamp so identical inputs produce identical bytes."""
    info = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    return info


def build_management_review_archive(
    tables: dict[str, pd.DataFrame], summary: dict[str, Any]
) -> bytes:
    """Build a deterministic ZIP with validated names and spreadsheet-safe CSVs."""
    if not isinstance(tables, dict) or not isinstance(summary, dict):
        raise ValueError("Management export requires table and summary dictionaries")

    validated_tables: list[tuple[str, pd.DataFrame]] = []
    seen_names: set[str] = set()
    for filename, frame in sorted(tables.items()):
        if (
            not isinstance(filename, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.csv", filename)
            or filename.casefold() in _RESERVED_ARCHIVE_NAMES
        ):
            raise ValueError(f"Invalid management export filename: {filename!r}")
        folded_name = filename.casefold()
        if folded_name in seen_names:
            raise ValueError(f"Duplicate management export filename: {filename}")
        if not isinstance(frame, pd.DataFrame):
            raise ValueError(f"Management export table must be a DataFrame: {filename}")
        seen_names.add(folded_name)
        validated_tables.append((filename, frame))

    try:
        summary_json = json.dumps(
            summary, indent=2, sort_keys=True, default=str, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Management export summary is not valid JSON: {exc}") from exc

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_archive_info("management_summary.json"), summary_json)
        for filename, frame in validated_tables:
            csv_text = _spreadsheet_safe_frame(frame).to_csv(index=False)
            archive.writestr(_archive_info(filename), csv_text)
    return buffer.getvalue()
