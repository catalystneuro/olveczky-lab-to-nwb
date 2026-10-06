"""Reconvert the ARID1B SOC1 sessions on the local drive to NWB, for Spyglass ingestion.

Uses the repo's own session_to_nwb() unchanged: the files are standard NWB (ndx-pose
0.4.0), nothing Spyglass-specific is added. One NWB file per rat; both rats of a session
share the session_id. The files are then copied into the Spyglass raw dir.

Run in the Windows conversion env (olveczky-lab-to-nwb-env):

    python spyglass/convert_sessions.py                 # all sessions, both rats
    python spyglass/convert_sessions.py 2022_10_17_M1_M2 1   # one session, rat 1
"""

import shutil
import sys
import time
from pathlib import Path

from olveczky_lab_to_nwb.klibaite_2025_rat.convert_session import (
    parse_session_folder_name,
    session_to_nwb,
)
from olveczky_lab_to_nwb.klibaite_2025_rat.utils.subject_metadata import get_subject_metadata

DATA_DIR = Path("F:/CN_data/Olveczky-CN-data-share/ugne")
COHORT, ENCOUNTER = "ARID1B", "SOC1"
SESSIONS = ["2022_10_17_M1_M2", "2022_10_17_M3_M4"]
RAT_LOG = DATA_DIR / "social_touch" / f"{COHORT}_{ENCOUNTER}" / "ugne_rat_log.xlsx"
OUTPUT_DIR = Path("F:/CN_data/olveczky-nwb-reconverted")
SPYGLASS_RAW_DIR = Path("F:/CN_data/olveczky-spyglass/spyglass_data/raw")


def convert_one(session: str, rat_idx: int) -> Path:
    session_dir = DATA_DIR / COHORT / f"{COHORT}_{ENCOUNTER}" / session
    parsed = parse_session_folder_name(session)
    rat_id = parsed["rat1_id"] if rat_idx == 1 else parsed["rat2_id"]
    subject_metadata = get_subject_metadata(rat_id=rat_id, cohort=COHORT, rat_log_path=RAT_LOG)
    contacts = DATA_DIR / "social_touch" / f"{COHORT}_{ENCOUNTER}" / session / "skin_contacts_symmetric.h5"
    assert contacts.exists(), contacts

    t0 = time.time()
    nwbfile_path = session_to_nwb(
        session_dir_path=session_dir,
        output_dir_path=OUTPUT_DIR,
        rat_idx=rat_idx,
        cohort=COHORT,
        encounter=ENCOUNTER,
        subject_metadata=subject_metadata,
        contacts_file_path=contacts,
        overwrite=True,
    )
    SPYGLASS_RAW_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(nwbfile_path, SPYGLASS_RAW_DIR / nwbfile_path.name)
    print(f"{session} rat{rat_idx} ({rat_id}): {nwbfile_path.name} in {time.time() - t0:.0f}s", flush=True)
    return nwbfile_path


def main() -> None:
    if len(sys.argv) == 3:
        jobs = [(sys.argv[1], int(sys.argv[2]))]
    else:
        jobs = [(s, r) for s in SESSIONS for r in (1, 2)]
    for session, rat_idx in jobs:
        convert_one(session, rat_idx)


if __name__ == "__main__":
    main()
