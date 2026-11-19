"""Interface writing the session's epoch and task, in the layout Spyglass reads, annotated with HED."""

import re

import numpy as np
from hdmf.common import DynamicTable, VectorData, VectorIndex
from ndx_hed import HedLabMetaData, HedTags
from neuroconv.basedatainterface import BaseDataInterface
from pydantic import FilePath
from pynwb.file import NWBFile

# Each NWB file holds one recording session, so it has one epoch.
_EPOCH_NUMBER = 1


class TaskEpochInterface(BaseDataInterface):
    """Write one epoch and one task row describing the session, and the lab's HED definitions.

    The layout follows what Spyglass ingests into ``IntervalList``, ``Task`` and ``TaskEpoch``:

    - ``nwbfile.epochs``: one row spanning the recording (Camera1's first to last frame time), tagged
      ``"01_<task_name>"``.
    - ``processing["tasks"]["task_table"]``: one row with ``task_name``, ``task_description``,
      ``task_environment``, ``camera_id`` (the trailing digits of each camera name, ``"Camera1"`` -> 1),
      ``task_epochs`` and ``HED``, a ``Def/`` reference to a lab definition.

    The HED schema version and the definitions are written once to ``HedLabMetaData``. The task and HED
    come from ``metadata["Task"]`` and ``metadata["HED"]`` (see ``general_metadata.yaml``).
    """

    keywords = ["task", "epoch", "HED"]

    def __init__(self, frametimes_file_path: FilePath, camera_names: list[str], verbose: bool = False):
        """
        Parameters
        ----------
        frametimes_file_path : FilePath
            Path to Camera1's ``frametimes.npy``. Its first and last frame times bound the epoch.
        camera_names : list of str
            Names of the cameras that recorded the task (``"Camera1"`` ... ``"Camera6"``).
        verbose : bool, default: False
        """
        self.verbose = verbose
        super().__init__(frametimes_file_path=frametimes_file_path, camera_names=camera_names)

    def get_metadata_schema(self) -> dict:
        metadata_schema = super().get_metadata_schema()
        metadata_schema["properties"]["Task"] = {
            "type": "object",
            "required": ["task_name", "task_description", "task_environment", "hed"],
            "properties": {
                key: {"type": "string"} for key in ("task_name", "task_description", "task_environment", "hed")
            },
        }
        metadata_schema["properties"]["HED"] = {
            "type": "object",
            "required": ["hed_schema_version", "definitions"],
            "properties": {
                "hed_schema_version": {"type": "string"},
                "definitions": {"type": "string"},
                "body_parts": {"type": "object"},  # read by SkinContactsInterface
            },
        }
        return metadata_schema

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict) -> None:
        task_metadata = metadata["Task"]
        nwbfile.add_lab_meta_data(
            HedLabMetaData(
                hed_schema_version=metadata["HED"]["hed_schema_version"],
                definitions=metadata["HED"]["definitions"],
            )
        )

        frame_times = np.load(self.source_data["frametimes_file_path"])[1]
        task_name = task_metadata["task_name"]
        nwbfile.add_epoch(
            start_time=float(frame_times[0]),
            stop_time=float(frame_times[-1]),
            tags=[f"{_EPOCH_NUMBER:02d}_{task_name}"],
        )

        camera_ids = [int(re.search(r"(\d+)$", name).group(1)) for name in self.source_data["camera_names"]]
        camera_id = VectorData(
            name="camera_id",
            description="IDs of the cameras that recorded the task: the trailing digits of each camera Device name.",
            data=np.array(camera_ids, dtype=np.int64),
        )
        task_epochs = VectorData(
            name="task_epochs",
            description="Epoch numbers in which the task ran.",
            data=np.array([_EPOCH_NUMBER], dtype=np.int64),
        )
        task_table = DynamicTable(
            name="task_table",
            description="Behavioral task of this session, in the layout Spyglass reads into Task and TaskEpoch.",
            columns=[
                VectorData(name="task_name", description="Name of the task.", data=[task_name]),
                VectorData(
                    name="task_description",
                    description="Description of the task.",
                    data=[task_metadata["task_description"]],
                ),
                VectorData(
                    name="task_environment",
                    description="Environment the animal was in.",
                    data=[task_metadata["task_environment"]],
                ),
                camera_id,
                VectorIndex(name="camera_id_index", data=[len(camera_ids)], target=camera_id),
                task_epochs,
                VectorIndex(name="task_epochs_index", data=[1], target=task_epochs),
                HedTags(description="HED annotation of the task.", data=[task_metadata["hed"]]),
            ],
        )
        tasks_module = nwbfile.create_processing_module(name="tasks", description="Behavioral task of this session.")
        tasks_module.add(task_table)
