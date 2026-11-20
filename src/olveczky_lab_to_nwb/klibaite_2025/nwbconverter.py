"""NWBConverter of the Klibaite 2025 conversion."""

import warnings
from pathlib import Path

import numpy as np
import scipy.io
from neuroconv import NWBConverter
from neuroconv.converters import DANNCEConverter

from olveczky_lab_to_nwb.klibaite_2025.interfaces import SkinContactsInterface, TaskEpochInterface


class Klibaite2025NWBConverter(NWBConverter):
    """Converter of one rat of one session of the Klibaite 2025 dataset.

    Interface slots:

    - ``DANNCE``: the rat's sDANNCE 3D pose (``save_data_AVG0.mat``), the 6 camera videos as external files and
      the calibrated cameras (``DANNCEConverter``).
    - ``SkinContacts``: the skin contacts between the two rats (``skin_contacts_symmetric.h5``), when the
      session has them.
    - ``TaskEpoch``: the session's epoch and task, and the HED definitions.

    Every stream is on the clock of the cameras' ``frametimes.npy`` (seconds from the start of the recording):
    the videos are timed by their own camera's frame times, the pose and the skin contacts by Camera1's.
    """

    data_interface_classes = dict(
        DANNCE=DANNCEConverter,
        SkinContacts=SkinContactsInterface,
        TaskEpoch=TaskEpochInterface,
    )

    def __init__(self, source_data: dict[str, dict], verbose: bool = False):
        # DANNCEConverter warns that the pose has no times, as no Label3D sync table is passed;
        # temporally_align_data_interfaces sets them.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="No timing information is available for the DANNCE")
            super().__init__(source_data=source_data, verbose=verbose)
        self.source_data = source_data

    def temporally_align_data_interfaces(self, metadata: dict | None = None, conversion_options: dict | None = None):
        """Time the pose by Camera1's frame times, at the frame of each prediction.

        The ``sampleID`` of each sDANNCE prediction is the Camera1 frame it was predicted on. The Label3D sync
        tables of the sessions that have one record the same mapping, so they are not read.
        """
        dannce = self.data_interface_objects["DANNCE"]
        pose_file_path = self.source_data["DANNCE"]["file_paths"]
        frametimes_file_path = Path(self.source_data["DANNCE"]["videos_folder_path"]) / "Camera1" / "frametimes.npy"

        sample_ids = np.ravel(scipy.io.loadmat(pose_file_path, variable_names=["sampleID"])["sampleID"])
        frames = sample_ids.astype("int64")
        frame_times = np.load(frametimes_file_path)[1]
        if not np.array_equal(frames, sample_ids) or frames.min() < 0 or frames.max() >= len(frame_times):
            raise ValueError(
                f"The sampleIDs of {pose_file_path} ({sample_ids.min()} to {sample_ids.max()}) are not frames of the "
                f"{len(frame_times)} frames of {frametimes_file_path}."
            )
        pose_metadata_key = dannce.data_interface_objects["DANNCE"].metadata_key
        dannce.temporal_alignment[pose_metadata_key].set_times(frame_times[frames])
