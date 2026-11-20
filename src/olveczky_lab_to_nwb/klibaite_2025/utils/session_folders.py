"""Read the session folders of the data share: session ID, date, rats and prediction file of each session.

There are two conditions. A social session holds a pair of rats, in <cohort>/<cohort>_SOC<N>/ (encounter round N)
or FX/FXmale_<group>/, named YYYY_MM_DD_M<a>_M<b>[_<suffix>]. A lone session holds one rat alone in the arena, in
FX/FXmale_wk1/ or LONGEVANS/LONGEVANS_M/, named YYYY_MM_DD_M<a>. See docs/data_organization.md.
"""

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from olveczky_lab_to_nwb.klibaite_2025.utils.subject_metadata import get_rat_colors

CONDITIONS = ("social", "lone")

# The prediction file of the FX social sessions, which holds the pose of both rats: pred is (n_frames, 2, 3, 23).
FX_SOCIAL_POSE_FILE = Path("SDANNCE") / "predict_results" / "save_data_AVG0.mat"

# Lone session group folder -> its sDANNCE prediction file. The Long-Evans lone sessions also have SDANNCE_5camfix/,
# fix-5cam/ or SDANNCE/ predictions, which are not read: bsl0.5_FM is the model of the social sessions and covers the
# whole recording. LONGEVANS_M_AMP and FXfemale07 have no prediction and are not lone session groups.
LONE_POSE_FILES = {
    "FXmale_wk1": Path("SDANNCE") / "predict_results" / "save_data_AVG0.mat",
    "LONGEVANS_M": Path("SDANNCE_x2") / "bsl0.5_FM" / "save_data_AVG0.mat",
}

_SOCIAL_FOLDER = re.compile(r"(\d{4})_(\d{2})_(\d{2})_(M\d+)_(M\d+)(?:_(\w+))?")
_LONE_FOLDER = re.compile(r"(\d{4})_(\d{2})_(\d{2})_(M\d+)")


def _start_time(year: str, month: str, day: str) -> datetime:
    """The session date at midnight in America/New_York: the time of day was not recorded."""
    return datetime(int(year), int(month), int(day), tzinfo=ZoneInfo("America/New_York"))


_ROUND_FOLDER = re.compile(r".*SOC(\d+)")
_FX_GROUP_FOLDER = re.compile(r"FXmale_((?:all|brothers|friends)\d+)")


def _take_number(session_dir_path: Path, rat_ids: tuple[str, str], date: str) -> int:
    """Count the recordings of the pair on the session's date in its folder, in folder name order, up to this one.

    ``LONGEVANS_M_SOC7/2022_12_07_M2_M5`` is take 1 and ``2022_12_07_M2_M5_take2`` take 2; on the share, only three
    pairs were recorded twice on one day.
    """
    takes = sorted(
        path.name
        for path in session_dir_path.parent.glob(f"{date}_M*_M*")
        if (match := _SOCIAL_FOLDER.fullmatch(path.name)) is not None
        and {match.group(4), match.group(5)} == set(rat_ids)
    )
    if session_dir_path.name not in takes:
        raise FileNotFoundError(f"{session_dir_path} does not exist.")
    return takes.index(session_dir_path.name) + 1


def parse_session_folder(session_dir_path: str | Path, condition: str) -> dict:
    """Read the session ID, start time, rats and encounter of a session from its folder path.

    - Social: ``social-<round>-<YYYYMMDD>[-<take>]-<rat a>-<rat b>``, the same in the files of both rats, with the
      rats in the order of the folder name. The round is the encounter round, or the pairing group for FX:
      ``SCN2A/SCN2A_SOC1/2022_09_22_M1_M2`` gives ``social-1-20220922-M1-M2`` and
      ``FX/FXmale_brothers2/2021_12_09_M2_M1`` gives ``social-brothers2-20211209-M2-M1``. The take is written only
      for the second recording of a pair on one day: ``LONGEVANS_M_SOC7/2022_12_07_M2_M5_take2`` gives
      ``social-7-20221207-2-M2-M5`` (see _take_number).
    - Lone: ``lone-<YYYYMMDD>-<rat>``: ``FX/FXmale_wk1/2021_12_05_M1`` gives ``lone-20211205-M1``.

    The session start time is the date at midnight in America/New_York.

    Raises
    ------
    ValueError
        If the folder is not a session folder of the condition.
    FileNotFoundError
        If a social session folder does not exist (the take is counted from the folders on the share).
    """
    session_dir_path = Path(session_dir_path)
    group = session_dir_path.parent.name
    if condition == "social":
        session_match = _SOCIAL_FOLDER.fullmatch(session_dir_path.name)
        round_match = _ROUND_FOLDER.fullmatch(group) or _FX_GROUP_FOLDER.fullmatch(group)
        if session_match is None or round_match is None:
            raise ValueError(
                f"{session_dir_path} is not a social session folder: expected <cohort>_SOC<N>/ or FXmale_<group>/ "
                "YYYY_MM_DD_M<a>_M<b>[_<suffix>]."
            )
        year, month, day, rat1_id, rat2_id, _ = session_match.groups()
        rat_ids = (rat1_id, rat2_id)
        take = _take_number(session_dir_path, rat_ids, date=f"{year}_{month}_{day}")
        session_id = "-".join(
            ["social", round_match.group(1), f"{year}{month}{day}", *([str(take)] if take > 1 else []), *rat_ids]
        )
        encounter = f"pairing group {group}" if group.startswith("FX") else f"encounter round {round_match.group(1)}"
    elif condition == "lone":
        session_match = _LONE_FOLDER.fullmatch(session_dir_path.name)
        if session_match is None or group not in LONE_POSE_FILES:
            raise ValueError(
                f"{session_dir_path} is not a lone session folder: expected one of {list(LONE_POSE_FILES)}/"
                "YYYY_MM_DD_M<a>."
            )
        year, month, day, rat_id = session_match.groups()
        session_id = f"lone-{year}{month}{day}-{rat_id}"
        encounter = f"lone session group {group}"
        rat_ids = (rat_id,)
    else:
        raise ValueError(f"Unknown condition {condition!r}; use one of {CONDITIONS}.")
    return dict(
        session_id=session_id,
        session_start_time=_start_time(year, month, day),
        rat_ids=rat_ids,
        encounter=encounter,
    )


def find_pose_file(session_dir_path: str | Path, condition: str, cohort: str, rat_idx: int) -> tuple[Path, int | None]:
    """Find the sDANNCE prediction file of a rat, and its animal index in the file (None for a one-animal file).

    - Social sessions: SDANNCE*/bsl0.5_FM_rat<rat_idx>/save_data_AVG0.mat. Sessions keep it in SDANNCE/, SDANNCE_x2/ or
      SDANNCE_x3/; when several have it, the copies are the same and the first is used. Other prediction folders
      (test runs) and files (save_data_AVG.mat, which misses the last 1000 frames) are not read.
    - FX social sessions: FX_SOCIAL_POSE_FILE, which holds both rats; rat1 (the blue rat) is index 0.
    - Lone sessions: the file of LONE_POSE_FILES for the group folder.
    """
    session_dir_path = Path(session_dir_path)
    if condition == "lone":
        return session_dir_path / LONE_POSE_FILES[session_dir_path.parent.name], None
    if cohort == "FX":
        return session_dir_path / FX_SOCIAL_POSE_FILE, rat_idx - 1
    pose_file_paths = sorted(session_dir_path.glob(f"SDANNCE*/bsl0.5_FM_rat{rat_idx}/save_data_AVG0.mat"))
    if not pose_file_paths:
        raise FileNotFoundError(f"No SDANNCE*/bsl0.5_FM_rat{rat_idx}/save_data_AVG0.mat in {session_dir_path}.")
    return pose_file_paths[0], None


def get_fx_rat_order(session_dir_path: str | Path, rat_log_path: str | Path) -> tuple[str, str]:
    """Return the blue and the red rat of an FX social session, from the rat log.

    In the FX prediction file, animal index 0 is the rat dyed blue and index 1 the rat dyed red: projected on the
    Camera1 video, index 0 lands on the blue-marked rat in FXmale_brothers2/2021_12_09_M2_M1,
    FXmale_friends1/2021_12_10_M1_M3 and FXmale_brothers1/2021_12_08_M1_M2 (the per-rat files of the other cohorts
    follow the same rule: rat1 is the blue rat). Which rat ID is blue comes from the rat log, and is not always the
    first rat of the folder name. When the log gives only the red rat, the other rat is blue.

    Raises
    ------
    ValueError
        If the rat log does not say which rat of the session is blue.
    """
    rat_ids = parse_session_folder(session_dir_path, condition="social")["rat_ids"]
    blue, red = get_rat_colors(rat_log_path=rat_log_path, cohort="FX", session_dir_path=session_dir_path)
    if blue is None and red in rat_ids:
        blue = rat_ids[1 - rat_ids.index(red)]
    if blue not in rat_ids:
        raise ValueError(f"The rat log does not say which rat of {session_dir_path} is blue (blue {blue}, red {red}).")
    other = rat_ids[1 - rat_ids.index(blue)]
    if red is not None and red != other:
        raise ValueError(f"The rat log gives blue {blue} and red {red} for {session_dir_path}.")
    return blue, other
