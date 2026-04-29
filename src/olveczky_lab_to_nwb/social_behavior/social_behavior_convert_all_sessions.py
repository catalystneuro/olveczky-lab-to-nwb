"""
Batch-convert all Olveczky Lab social behavior sessions to NWB.

Walks the data root, discovers all genotype groups and encounter rounds, and
calls ``convert_session`` for each session folder.

Data root layout expected:
    <data_root>/ugne/
        <genotype>/                       # e.g. SCN2A, ARID1B
            <genotype>_SOC<N>/            # e.g. SCN2A_SOC1
                <YYYY_MM_DD_M{a}_M{b}>/   # one folder per session
                    videos/
                    SDANNCE/ or SDANNCE_x2/
                    ...
    social_touch/
        <genotype>_SOC<N>/
            <YYYY_MM_DD_M{a}_M{b}>/
                skin_contacts_symmetric.h5

Usage
-----
python social_behavior_convert_all_sessions.py \\
    --data_root  /path/to/ugne \\
    --output_dir /path/to/nwb_output \\
    [--genotypes SCN2A ARID1B] \\
    [--stub_test]
"""

from __future__ import annotations

import argparse
import traceback
from pathlib import Path

from olveczky_lab_to_nwb.social_behavior.social_behavior_convert_session import convert_session

# Genotype groups that have full session data (videos + SDANNCE) in the share.
DEFAULT_GENOTYPES = ["SCN2A", "ARID1B"]


def discover_sessions(data_root: Path, genotypes: list[str]) -> list[dict]:
    """
    Walk the data root and return a list of session dicts.

    Each dict has keys:
        session_dir, genotype, encounter, contacts_file (Path or None)
    """
    sessions = []
    social_touch_root = data_root / "social_touch"

    for genotype in genotypes:
        genotype_dir = data_root / genotype
        if not genotype_dir.exists():
            print(f"[SKIP] Genotype directory not found: {genotype_dir}")
            continue

        for encounter_dir in sorted(genotype_dir.iterdir()):
            if not encounter_dir.is_dir() or encounter_dir.name.startswith("."):
                continue

            # Parse encounter round from folder name, e.g. "SCN2A_SOC1" → "SOC1"
            encounter = encounter_dir.name.replace(f"{genotype}_", "")

            for session_dir in sorted(encounter_dir.iterdir()):
                if not session_dir.is_dir() or session_dir.name.startswith("."):
                    continue

                # Look for the corresponding skin contacts file in social_touch/.
                contacts_file = social_touch_root / f"{genotype}_{encounter}" / session_dir.name / "skin_contacts_symmetric.h5"
                if not contacts_file.exists():
                    contacts_file = None

                sessions.append(
                    dict(
                        session_dir=session_dir,
                        genotype=genotype,
                        encounter=encounter,
                        contacts_file=contacts_file,
                    )
                )

    return sessions


def convert_all_sessions(
    data_root: Path,
    output_dir: Path,
    genotypes: list[str] | None = None,
    rat_log_path: Path | None = None,
    recording_info_path: Path | None = None,
    stub_test: bool = False,
) -> None:
    """
    Convert all sessions to NWB.

    Parameters
    ----------
    data_root : Path
        Path to the ``ugne/`` directory (contains genotype subdirectories).
    output_dir : Path
        Root output directory.  NWB files are written to
        ``output_dir/<genotype>/<encounter>/``.
    genotypes : list of str, optional
        Restrict conversion to these genotype groups.
        Defaults to :data:`DEFAULT_GENOTYPES`.
    rat_log_path : Path, optional
        Path to ``ugne_rat_log.xlsx`` for per-rat DOB lookup.
    recording_info_path : Path, optional
        Path to ``ugne_recording_info.xlsx`` for genotype (WT/KO) lookup.
    stub_test : bool
        If True, convert only the first 100 frames of every session.
    """
    data_root = Path(data_root)
    output_dir = Path(output_dir)

    if genotypes is None:
        genotypes = DEFAULT_GENOTYPES

    sessions = discover_sessions(data_root, genotypes)
    print(f"Found {len(sessions)} sessions across genotypes: {genotypes}\n")

    n_ok = 0
    n_fail = 0

    for i, s in enumerate(sessions, start=1):
        session_output_dir = output_dir / s["genotype"] / s["encounter"]
        print(f"[{i}/{len(sessions)}] {s['genotype']} / {s['encounter']} / {s['session_dir'].name}")
        try:
            convert_session(
                session_dir=s["session_dir"],
                output_dir=session_output_dir,
                genotype=s["genotype"],
                encounter=s["encounter"],
                contacts_file=s["contacts_file"],
                rat_log_path=rat_log_path,
                recording_info_path=recording_info_path,
                stub_test=stub_test,
            )
            n_ok += 1
        except Exception:
            print(f"  [ERROR] Conversion failed:")
            traceback.print_exc()
            n_fail += 1

    print(f"\nDone. {n_ok} succeeded, {n_fail} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch-convert Olveczky Lab social behavior sessions to NWB."
    )
    parser.add_argument("--data_root", type=Path, required=True, help="Path to ugne/ data directory.")
    parser.add_argument("--output_dir", type=Path, required=True, help="Root output directory for NWB files.")
    parser.add_argument(
        "--genotypes",
        nargs="+",
        default=DEFAULT_GENOTYPES,
        help=f"Genotype groups to convert (default: {DEFAULT_GENOTYPES}).",
    )
    parser.add_argument("--rat_log_path", type=Path, default=None, help="Path to ugne_rat_log.xlsx.")
    parser.add_argument(
        "--recording_info_path", type=Path, default=None, help="Path to ugne_recording_info.xlsx."
    )
    parser.add_argument("--stub_test", action="store_true", help="Convert only first 100 frames for testing.")
    args = parser.parse_args()

    convert_all_sessions(
        data_root=args.data_root,
        output_dir=args.output_dir,
        genotypes=args.genotypes,
        rat_log_path=args.rat_log_path,
        recording_info_path=args.recording_info_path,
        stub_test=args.stub_test,
    )
