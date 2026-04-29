"""Load per-rat subject metadata from the lab's Excel spreadsheets."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def get_subject_metadata(
    rat_id: str,
    cohort: str,
    rat_log_path: Path,
    recording_info_path: Path | None = None,
) -> dict:
    """Return subject metadata dict for one rat.

    Reads from ``ugne_rat_log.xlsx`` (sheet named ``cohort``).  The sheet has a
    two-row preamble: row 0 is a ``GENERAL INFO`` banner, row 1 is the actual
    column header (``Strain``, ``Rat ID``, ``DOB``, ``Genotype``, ``Initial Weight``, …).

    ``recording_info_path`` is accepted for forward-compatibility but currently
    not needed — genotype is already in the rat log.

    Parameters
    ----------
    rat_id : str
        Rat identifier within the cohort, e.g. ``"M1"``.
    cohort : str
        Cohort/genotype label matching the sheet name, e.g. ``"SCN2A"``.
    rat_log_path : Path
        Path to ``ugne_rat_log.xlsx``.
    recording_info_path : Path, optional
        Unused; kept for API compatibility.

    Returns
    -------
    dict
        Keys: subject_id, sex, date_of_birth (ISO 8601 UTC string),
        strain, genotype, weight, description.

    Raises
    ------
    KeyError
        If ``rat_id`` is not found in the cohort sheet.
    """
    import pandas as pd

    rat_log = pd.read_excel(rat_log_path, sheet_name=cohort, header=1, dtype=str)
    rat_log.columns = rat_log.columns.str.strip()

    rat_col = _find_column(rat_log, ["Rat ID", "RAT ID", "rat id", "RAT", "Rat"])
    dob_col = _find_column(rat_log, ["DOB", "dob", "DOB YYYYMMDD"])
    genotype_col = _find_column(rat_log, ["Genotype", "GENOTYPE", "genotype"])
    weight_col = _find_column(rat_log, ["Initial Weight", "Weight", "weight", "WEIGHT"])

    mask = rat_log[rat_col].str.strip().str.upper() == rat_id.strip().upper()
    if not mask.any():
        raise KeyError(f"Rat '{rat_id}' not found in sheet '{cohort}' of {rat_log_path}")

    row = rat_log[mask].iloc[0]

    date_of_birth = _parse_dob(str(row[dob_col]).strip())
    genotype = str(row[genotype_col]).strip()
    weight_raw = str(row[weight_col]).strip()
    weight = _normalize_weight(weight_raw)

    result = {
        "subject_id": f"{cohort}-{rat_id}",
        "sex": "U",
        "date_of_birth": date_of_birth,
        "strain": "Long Evans",
        "genotype": genotype,
        "description": f"Rat {rat_id} from cohort {cohort}. Genotype: {genotype}.",
    }
    if weight:
        result["weight"] = weight
    return result


def _find_column(df, candidates: list[str]) -> str:
    """Return the first column name from *candidates* that exists in *df*."""
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"None of {candidates} found in columns {list(df.columns)}")


def _parse_dob(dob_raw: str) -> str:
    """Convert a DOB value to ISO 8601 UTC datetime string."""
    dob_raw = dob_raw.split(".")[0].strip()

    # pandas may read date cells as "2022-06-16 00:00:00"
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(dob_raw, fmt)
            return dt.replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            continue

    # Plain 8-digit integer string YYYYMMDD
    if len(dob_raw) == 8 and dob_raw.isdigit():
        dt = datetime(int(dob_raw[:4]), int(dob_raw[4:6]), int(dob_raw[6:8]), tzinfo=timezone.utc)
        return dt.isoformat()

    from dateutil import parser as dateutil_parser

    dt = dateutil_parser.parse(dob_raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _normalize_weight(weight_raw: str) -> str | None:
    """Return weight as '[numeric] kg', converting g/mg if needed, or None."""
    if not weight_raw or weight_raw.lower() in ("nan", "none", ""):
        return None
    import re

    m = re.match(r"^(\d+(?:\.\d+)?)\s*(kg|g|mg)$", weight_raw.strip())
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2)
    if unit == "g":
        value /= 1000
    elif unit == "mg":
        value /= 1_000_000
    return f"{value:.4g} kg"
