"""Load per-rat subject metadata from the lab's Excel spreadsheets."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

STRAINS: dict = (
    {  # from paper: https://www.cell.com/cell/fulltext/S0092-8674(25)00154-0#:~:text=Experimental%20models%3A%20Organisms/strains
        "LongEvans": {
            "strain": "LE-Scn2a-em1Mcwi",
            "supplier": "Charles River Laboratories",
            "RRID": "Strain code: 006",
        },
        "SCN2A": {"strain": "LE-Scn2a-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_25394530"},
        "CNTNAP": {"strain": "LE-Cntnap2-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_25330087"},
        "CHD8": {"strain": "LE-Chd8-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_25330088"},
        "GRIN2B": {"strain": "LE-Grin2b-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_14394515"},
        "ARID1B": {"strain": "LE-Arid1b-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_14394518"},
        "FRAGILEX": {"strain": "LE-Fmr1-em2Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_11553873"},
        "NRXN1": {"strain": "LE-Nrxn1-em1Mcwi", "supplier": "Medical College of Wisconsin", "RRID": "RGD_25330089"},
    }
)


def get_subject_metadata(
    rat_id: str,
    cohort: str,
    rat_log_path: Path,
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
        Cohort label matching the sheet name, e.g. ``"SCN2A"``.
    rat_log_path : Path
        Path to ``ugne_rat_log.xlsx``.

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

    rat_col = "Rat ID"  # _find_column(rat_log, ["Rat ID", "RAT ID", "rat id", "RAT", "Rat"])
    dob_col = "DOB"  # _find_column(rat_log, ["DOB", "dob", "DOB YYYYMMDD"])
    genotype_col = "Genotype"  # _find_column(rat_log, ["Genotype", "GENOTYPE", "genotype"])
    # weight_col = _find_column(rat_log, ["Initial Weight", "Weight", "weight", "WEIGHT"])
    markings_col = "Markings"
    cage_col = "Cage"
    mother_col = "Mother"
    mask = rat_log[rat_col].str.strip().str.upper() == rat_id.strip().upper()
    if not mask.any():
        raise KeyError(f"Rat '{rat_id}' not found in sheet '{cohort}' of {rat_log_path}")

    row = rat_log[mask].iloc[0]

    date_of_birth = _parse_dob(str(row[dob_col]).strip())
    genotype = str(row[genotype_col]).strip()
    # weight_raw = str(row[weight_col]).strip()
    # weight = _normalize_weight(weight_raw)
    marking = str(row[markings_col]).strip()
    cage = str(
        row[cage_col]
    ).strip()  # TODO return nan because the cells are merged (except for the first row of the corresponding merged cells) --> trace back to the first non nan value
    mother = str(
        row[mother_col]
    ).strip()  # TODO return nan because the cells are merged (except for the first row of the corresponding merged cells) --> trace back to the first non nan value

    result = {
        "subject_id": f"{cohort}-{rat_id}",
        "sex": "U",  # TODO extract from rat_id: M# --> male / F# --> female
        "date_of_birth": date_of_birth,
        "strain": STRAINS[cohort]["strain"],
        "genotype": genotype,
        "description": f"Rat {rat_id} from cohort {cohort}. Marking: {marking}. Cage: {cage}. Mother: {mother}. Supplier: {STRAINS[cohort]['supplier']}. RRID: {STRAINS[cohort]['RRID']}",
    }
    # if weight:
    #     result["weight"] = weight
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


if __name__ == "__main__":
    rat_log_path = Path("H:/Olveczky-CN-data-share/ugne/ugne_rat_log.xlsx")
    metadata = get_subject_metadata(rat_id="M1", cohort="ARID1B", rat_log_path=rat_log_path)
    print(metadata)
