"""Subject metadata of each rat, from the lab's rat log (ugne_rat_log.xlsx)."""

from pathlib import Path

import pandas as pd

# One entry per cohort folder of the data share. "sheet" is the rat log sheet of the cohort,
# "strain" the strain designation of the paper (Key resources table), which is also the key of
# its RRID under ExternalResources.strain in general_metadata.yaml. "gene" is the targeted gene of
# the knockout lines; the mutant allele is named by the end of the strain name (LE-Scn2a-em1Mcwi
# carries Scn2a<em1Mcwi>, made by CRISPR in Long-Evans embryos).
COHORTS = {
    "SCN2A": dict(sheet="SCN2A", strain="LE-Scn2a-em1Mcwi", supplier="Medical College of Wisconsin", gene="Scn2a"),
    "ARID1B": dict(sheet="ARID1B", strain="LE-Arid1b-em1Mcwi", supplier="Medical College of Wisconsin", gene="Arid1b"),
    "CHD8": dict(sheet="CHD8", strain="LE-Chd8-em1Mcwi", supplier="Medical College of Wisconsin", gene="Chd8"),
    "GRINB": dict(sheet="GRINB", strain="LE-Grin2b-em1Mcwi", supplier="Medical College of Wisconsin", gene="Grin2b"),
    "NRXN1": dict(sheet="NRXN1", strain="LE-Nrxn1-em1Mcwi", supplier="Medical College of Wisconsin", gene="Nrxn1"),
    "LONGEVANS": dict(sheet="LongEvans", strain="Long-Evans", supplier="Charles River Laboratories"),
}

# Genotype column of the rat log (upper case) -> number of mutant alleles. ARID1B writes
# "KO wt" and "KO Het"; the other sheets "WT" and "Het".
MUTANT_ALLELE_COUNT = {"WT": 0, "KO WT": 0, "HET": 1, "KO HET": 1}

# Age range of the rats of a cohort whose sheet has no dates of birth, from the paper's methods:
# the Long-Evans rats were "aged 9-14 weeks" (Klibaite et al., bioRxiv 2024.09.27.615451, Methods).
AGE_WITHOUT_DATE_OF_BIRTH = {"LONGEVANS": "P9W/P14W"}


def read_rat_table(rat_log_path: str | Path, cohort: str) -> pd.DataFrame:
    """Read the table of rats of a cohort from the rat log, indexed by rat ID (e.g. "M1").

    Each sheet has a banner row, then the rat table (one row per rat), a blank row, and a table of
    recordings, which is not read. Cage and Mother are merged cells shared by the rats of a cage,
    so they are filled down.
    """
    sheet = pd.read_excel(rat_log_path, sheet_name=COHORTS[cohort]["sheet"], header=1, dtype=str)
    sheet.columns = sheet.columns.str.strip()
    first_blank_row = sheet["Rat ID"].isna().idxmax() if sheet["Rat ID"].isna().any() else len(sheet)
    rats = sheet.iloc[:first_blank_row].copy()
    for column in ("Cage", "Mother"):
        if column in rats.columns and rats[column].notna().any():
            rats[column] = rats[column].ffill()
    rats["Rat ID"] = rats["Rat ID"].str.strip().str.upper()
    return rats.set_index("Rat ID")


def format_genotype(rat_log_genotype: str, cohort: str) -> str:
    """Write a rat log genotype in allele notation, with the allele in angle brackets.

    For SCN2A, "WT" gives "Scn2a<+>/Scn2a<+>" and "Het" gives "Scn2a<em1Mcwi>/Scn2a<+>".

    Raises
    ------
    ValueError
        If the genotype is not one of MUTANT_ALLELE_COUNT.
    """
    key = " ".join(rat_log_genotype.upper().split())
    if key not in MUTANT_ALLELE_COUNT:
        raise ValueError(
            f"Genotype {rat_log_genotype!r} of cohort {cohort} is not one of {list(MUTANT_ALLELE_COUNT)}; "
            "add it to MUTANT_ALLELE_COUNT in utils/subject_metadata.py."
        )
    gene = COHORTS[cohort]["gene"]
    mutant_allele = f"{gene}<{COHORTS[cohort]['strain'].rsplit('-', 1)[-1]}>"
    alleles = [mutant_allele] * MUTANT_ALLELE_COUNT[key] + [f"{gene}<+>"] * (2 - MUTANT_ALLELE_COUNT[key])
    return "/".join(alleles)


def get_subject_metadata(rat_id: str, cohort: str, rat_log_path: str | Path) -> dict:
    """Return the NWB Subject fields of one rat.

    All rats are male. Weights were not recorded. Genotype and date of birth are written when the
    cohort's sheet has them (the CHD8 and NRXN1 sheets have no genotype, the LongEvans sheet no date
    of birth). Without a date of birth, the age range of AGE_WITHOUT_DATE_OF_BIRTH is written.

    Parameters
    ----------
    rat_id : str
        Rat ID within the cohort, e.g. "M1".
    cohort : str
        Cohort folder name, a key of COHORTS.
    rat_log_path : str or Path
        Path to ugne_rat_log.xlsx.

    Raises
    ------
    KeyError
        If the rat is not in the cohort's sheet.
    """
    rats = read_rat_table(rat_log_path, cohort)
    if rat_id.upper() not in rats.index:
        raise KeyError(f"Rat {rat_id} is not in sheet {COHORTS[cohort]['sheet']!r} of {rat_log_path}.")
    rat = rats.loc[rat_id.upper()].dropna().str.strip()

    details = [f"{column}: {rat[column]}." for column in ("Markings", "Cage", "Mother") if column in rat]
    subject = dict(
        subject_id=f"{cohort}-{rat_id}",
        sex="M",
        strain=COHORTS[cohort]["strain"],
        description=" ".join(
            [f"Rat {rat_id} of cohort {cohort}.", *details, f"Supplier: {COHORTS[cohort]['supplier']}."]
        ),
    )
    if "Genotype" in rat:
        subject["genotype"] = format_genotype(rat["Genotype"], cohort)
    if "DOB" in rat:
        subject["date_of_birth"] = pd.Timestamp(rat["DOB"]).tz_localize("America/New_York").isoformat()
    elif cohort in AGE_WITHOUT_DATE_OF_BIRTH:
        subject["age"] = AGE_WITHOUT_DATE_OF_BIRTH[cohort]
    return subject
