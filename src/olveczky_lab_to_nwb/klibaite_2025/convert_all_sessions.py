"""Convert every session of the Klibaite 2025 dataset to NWB, two files per session (one per rat).

The data share folder (ugne/) holds one folder per cohort, with one folder per encounter round
(<cohort>_SOC<N>, or LONGEVANS_M_SOC<N>) and one folder per session; the skin contacts are in
social_touch/<encounter folder>/<session folder>/skin_contacts_symmetric.h5. See docs/data_organization.md.
"""

import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from pprint import pformat

from tqdm import tqdm

from olveczky_lab_to_nwb.klibaite_2025.convert_session import parse_session_folder, session_to_nwb
from olveczky_lab_to_nwb.klibaite_2025.utils.subject_metadata import COHORTS


def get_session_to_nwb_kwargs_per_session(*, data_dir_path: str | Path, cohorts: list[str] | None = None) -> list[dict]:
    """List the arguments of session_to_nwb for each rat of each session.

    The session folders are the folders of <cohort>/*SOC<N>/ named YYYY_MM_DD_M<a>_M<b>[_<suffix>]; other folders
    (solo sessions, test runs, scripts) are left out.

    Parameters
    ----------
    data_dir_path : str or Path
        The ugne/ folder of the data share.
    cohorts : list of str, optional
        Cohorts to convert. Defaults to all cohorts of COHORTS.
    """
    data_dir_path = Path(data_dir_path)
    kwargs_per_session = []
    for cohort in cohorts or COHORTS:
        for session_dir_path in sorted((data_dir_path / cohort).glob("*SOC*/*")):
            try:
                parse_session_folder(session_dir_path)
            except ValueError:
                continue
            contacts_file_path = (
                data_dir_path
                / "social_touch"
                / session_dir_path.parent.name
                / session_dir_path.name
                / "skin_contacts_symmetric.h5"
            )
            for rat_idx in (1, 2):
                kwargs_per_session.append(
                    dict(
                        session_dir_path=session_dir_path,
                        rat_idx=rat_idx,
                        cohort=cohort,
                        rat_log_path=data_dir_path / "ugne_rat_log.xlsx",
                        contacts_file_path=contacts_file_path if contacts_file_path.exists() else None,
                    )
                )
    return kwargs_per_session


def safe_session_to_nwb(*, session_to_nwb_kwargs: dict, exception_file_path: Path) -> None:
    """Run session_to_nwb, writing the arguments and the traceback to exception_file_path if it fails."""
    exception_file_path.unlink(missing_ok=True)  # from an earlier run
    try:
        session_to_nwb(**session_to_nwb_kwargs)
    except Exception:
        exception_file_path.write_text(f"{pformat(session_to_nwb_kwargs)}\n\n{traceback.format_exc()}")


def dataset_to_nwb(
    *,
    data_dir_path: str | Path,
    output_dir_path: str | Path,
    cohorts: list[str] | None = None,
    max_workers: int = 1,
    stub_test: bool = False,
    overwrite: bool = False,
    verbose: bool = False,
) -> None:
    """Convert every session of the data share.

    A rat-session that fails does not stop the others: its arguments and traceback are written to
    <output_dir_path>/exceptions/ERROR_<encounter folder>_<session folder>_rat<1 or 2>.txt.

    Parameters
    ----------
    data_dir_path : str or Path
        The ugne/ folder of the data share.
    output_dir_path : str or Path
        Folder of the NWB files.
    cohorts : list of str, optional
        Cohorts to convert. Defaults to all cohorts of COHORTS.
    max_workers : int, default: 1
        Number of rat-sessions converted in parallel.
    stub_test : bool, default: False
        Write stub files (see session_to_nwb) to <output_dir_path>/nwb_stub/.
    overwrite : bool, default: False
        Replace existing files. Otherwise rat-sessions whose file exists are skipped, which converts only new
        sessions.
    verbose : bool, default: False
    """
    output_dir_path = Path(output_dir_path)
    exception_dir_path = output_dir_path / "exceptions"
    exception_dir_path.mkdir(parents=True, exist_ok=True)

    kwargs_per_session = get_session_to_nwb_kwargs_per_session(data_dir_path=data_dir_path, cohorts=cohorts)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for kwargs in kwargs_per_session:
            session_dir_path = kwargs["session_dir_path"]
            exception_file_path = (
                exception_dir_path
                / f"ERROR_{session_dir_path.parent.name}_{session_dir_path.name}_rat{kwargs['rat_idx']}.txt"
            )
            kwargs.update(output_dir_path=output_dir_path, stub_test=stub_test, overwrite=overwrite, verbose=verbose)
            futures.append(
                executor.submit(
                    safe_session_to_nwb, session_to_nwb_kwargs=kwargs, exception_file_path=exception_file_path
                )
            )
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Converting rat-sessions"):
            pass


if __name__ == "__main__":
    data_dir_path = Path("/path/to/ugne")  # the ugne/ folder of the data share
    output_dir_path = Path("/path/to/nwbfiles")

    dataset_to_nwb(
        data_dir_path=data_dir_path,
        output_dir_path=output_dir_path,
        max_workers=2,  # see docs/converting_sessions.md: up to 18 GB per rat-session
        stub_test=False,
        overwrite=False,
    )
