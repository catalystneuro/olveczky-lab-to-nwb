"""
Batch-convert all Klibaite 2025 - Rat social behavior sessions to NWB.

Walks the data root, discovers all cohort groups and encounter rounds, and
calls ``session_to_nwb`` for each rat within each session folder.

Data root layout expected:
    <data_root>/ugne/
        <cohort>/                       # e.g. SCN2A, ARID1B
            <cohort>_SOC<N>/            # e.g. SCN2A_SOC1
                <YYYY_MM_DD_M{a}_M{b}>/   # one folder per session
                    videos/
                    SDANNCE/ or SDANNCE_x2/
                    ...
    social_touch/
        <cohort>_SOC<N>/
            <YYYY_MM_DD_M{a}_M{b}>/
                skin_contacts_symmetric.h5
"""

from __future__ import annotations

import re
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat
from typing import Union

from tqdm import tqdm

from olveczky_lab_to_nwb.klibaite_2025_rat.convert_session import parse_session_folder_name, session_to_nwb
from olveczky_lab_to_nwb.klibaite_2025_rat.utils.subject_metadata import get_subject_metadata

# Cohort groups that have full session data (videos + SDANNCE) in the share.
DEFAULT_COHORTS = [
    "SCN2A",
    "ARID1B",
    "CHD8",
    "GRINB",
    "NRXN1",
    "LONGEVANS",
]  # LONGEVANS skipping for now need clarification


def get_session_to_nwb_kwargs_per_session(
    *,
    data_dir_path: Union[str, Path],
    cohorts: list[str] | None = None,
    rat_log_path: Union[str, Path, None] = None,
) -> list[dict]:
    """Discover all sessions (one entry per rat per session) and return kwargs for each.

    Parameters
    ----------
    data_dir_path : str or Path
        Path to the ``ugne/`` directory (contains cohort subdirectories).
    cohorts : list of str, optional
        Restrict conversion to these cohort groups.
        Defaults to :data:`DEFAULT_COHORTS`.
    rat_log_path : str or Path, optional
        Path to ``ugne_rat_log.xlsx`` for per-rat DOB lookup. When omitted, or
        when a rat is missing from the log, that rat's NWB Subject metadata
        falls back to the converter's placeholders.

    Returns
    -------
    list of dict
        One dict per rat-session containing kwargs for `session_to_nwb`.
    """
    data_dir_path = Path(data_dir_path)
    if rat_log_path is not None:
        rat_log_path = Path(rat_log_path)
    if cohorts is None:
        cohorts = DEFAULT_COHORTS

    social_touch_root = data_dir_path / "social_touch"

    kwargs_list = []
    for cohort in cohorts:
        cohort_dir = data_dir_path / cohort
        if not cohort_dir.exists():
            print(f"[SKIP] Cohort directory not found: {cohort_dir}")
            continue

        for encounter_dir in sorted(cohort_dir.iterdir()):
            if not encounter_dir.is_dir() or encounter_dir.name.startswith("."):
                continue

            # Parse encounter round from folder name, e.g. "SCN2A_SOC1" -> "SOC1",
            # "LONGEVANS_M_SOC1" -> "SOC1" (LONGEVANS folders have an extra "M" segment).
            encounter_match = re.search(r"(SOC\d+)$", encounter_dir.name)
            if encounter_match is None:
                # e.g. LONGEVANS_M (solo baseline) / LONGEVANS_M_AMP (amphetamine, solo) folders:
                # not a two-rat social encounter, out of scope for this pair-based pipeline.
                print(f"  [SKIP] Encounter folder is not a social (SOC<N>) round, skipping: {encounter_dir}")
                continue
            encounter = encounter_match.group(1)

            for session_dir in sorted(encounter_dir.iterdir()):
                if not session_dir.is_dir() or session_dir.name.startswith("."):
                    continue

                # Look for the corresponding skin contacts file in social_touch/. The social_touch
                # subfolder name matches the raw encounter_dir name (e.g. "LONGEVANS_M_SOC6", not
                # the reconstructed "LONGEVANS_SOC6"), so use encounter_dir.name directly.
                contacts_file_path = (
                    social_touch_root / encounter_dir.name / session_dir.name / "skin_contacts_symmetric.h5"
                )
                if not contacts_file_path.exists():
                    contacts_file_path = None

                try:
                    parsed = parse_session_folder_name(session_dir.name)
                except ValueError as exc:
                    print(f"  [SKIP] {exc}")
                    continue
                rat_ids = {1: parsed["rat1_id"], 2: parsed["rat2_id"]}

                for rat_idx, rat_id in rat_ids.items():
                    subject_metadata = {}
                    if rat_log_path is not None:
                        try:
                            subject_metadata = get_subject_metadata(rat_id, cohort, rat_log_path)
                        except Exception as exc:
                            print(f"  [WARNING] Could not load subject metadata for {rat_id}: {exc}")

                    kwargs_list.append(
                        dict(
                            session_dir_path=session_dir,
                            rat_idx=rat_idx,
                            cohort=cohort,
                            encounter=encounter,
                            subject_metadata=subject_metadata,
                            contacts_file_path=contacts_file_path,
                        )
                    )

    return kwargs_list


def safe_session_to_nwb(
    *,
    session_to_nwb_kwargs: dict,
    exception_file_path: Union[Path, str],
) -> None:
    exception_file_path = Path(exception_file_path)
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception:
        with open(exception_file_path, mode="w") as f:
            f.write(f"session_to_nwb_kwargs:\n{pformat(session_to_nwb_kwargs)}\n\n")
            f.write(traceback.format_exc())


def safe_session_pair_to_nwb(
    *,
    session_to_nwb_kwargs_list: list[dict],
    exception_file_paths: list[Path],
) -> None:
    """Convert both rats of one session sequentially, in the same process.

    Both rats of a session share the same (often 5-55M row) ``skin_contacts_symmetric.h5``
    file. Running them as one task instead of two independent executor tasks lets
    ``SkinContactsInterface``'s module-level raw-data cache (see
    ``interfaces/skin_contacts_interface.py``) serve the second rat's read from memory instead
    of re-reading and re-decoding the file from disk. See ``documentation/performance_report.md``.
    """
    for kwargs, exception_file_path in zip(session_to_nwb_kwargs_list, exception_file_paths):
        safe_session_to_nwb(session_to_nwb_kwargs=kwargs, exception_file_path=exception_file_path)


def dataset_to_nwb(
    *,
    data_dir_path: Union[str, Path],
    output_dir_path: Union[str, Path],
    cohorts: list[str] | None = None,
    rat_log_path: Union[str, Path, None] = None,
    max_workers: int = 1,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
) -> None:
    """Convert the entire Klibaite 2025 Rat social behavior dataset to NWB.

    Parameters
    ----------
    data_dir_path : str or Path
        Path to the ``ugne/`` directory (contains cohort subdirectories).
    output_dir_path : str or Path
        Root output directory. NWB files are written to
        ``output_dir_path/<cohort>/<encounter>/``.
    cohorts : list of str, optional
        Restrict conversion to these cohort groups.
        Defaults to :data:`DEFAULT_COHORTS`.
    rat_log_path : str or Path, optional
        Path to ``ugne_rat_log.xlsx`` for per-rat DOB lookup.
    max_workers : int
        Number of parallel workers.
    stub_test : bool
        If True, convert only the first 100 frames of every session.
    overwrite : bool
        Overwrite existing NWB files.
    verbose : bool
        Print progress.
    """
    data_dir_path = Path(data_dir_path)
    output_dir_path = Path(output_dir_path)
    exception_dir = output_dir_path / "exceptions"
    exception_dir.mkdir(parents=True, exist_ok=True)

    kwargs_list = get_session_to_nwb_kwargs_per_session(
        data_dir_path=data_dir_path,
        cohorts=cohorts,
        rat_log_path=rat_log_path,
    )
    print(f"Found {len(kwargs_list)} rat-sessions across cohorts: {cohorts or DEFAULT_COHORTS}\n")

    # Group kwargs into (rat1, rat2) pairs per session -- session discovery above always emits
    # exactly one entry per rat, rat1 immediately followed by rat2, for each session. Submitting
    # both as a single executor task (rather than two independent ones) keeps them in the same
    # process, so SkinContactsInterface's raw-data cache can serve the second rat from memory
    # instead of re-reading their shared skin_contacts_symmetric.h5 file. See
    # `safe_session_pair_to_nwb` and `documentation/performance_report.md`.
    futures = []
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        for pair_start in range(0, len(kwargs_list), 2):
            pair_kwargs = kwargs_list[pair_start : pair_start + 2]
            exception_file_paths = []
            for kwargs in pair_kwargs:
                kwargs["output_dir_path"] = output_dir_path
                kwargs["stub_test"] = stub_test
                kwargs["overwrite"] = overwrite
                kwargs["verbose"] = verbose
                session_id = kwargs["session_dir_path"].name
                rat_idx = kwargs["rat_idx"]
                exception_file_paths.append(
                    exception_dir / f"ERROR_{kwargs['cohort']}_{kwargs['encounter']}_{session_id}_rat{rat_idx}.txt"
                )
            futures.append(
                executor.submit(
                    safe_session_pair_to_nwb,
                    session_to_nwb_kwargs_list=pair_kwargs,
                    exception_file_paths=exception_file_paths,
                )
            )

        for _ in tqdm(as_completed(futures), total=len(futures), desc="Converting session pairs"):
            pass


if __name__ == "__main__":
    data_dir_path = Path("H:/Olveczky-CN-data-share/ugne")
    output_dir_path = Path("H:/olveczky-nwbfiles")
    rat_log_path = data_dir_path / "ugne_rat_log.xlsx"

    dataset_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        cohorts=None,
        rat_log_path=rat_log_path,
        max_workers=1,
        stub_test=True,
        overwrite=True,
        verbose=True,
    )
