"""
Skin contacts interface for the Klibaite 2025 - Rat social behavior conversion.

Reads ``skin_contacts_symmetric.h5`` and writes a DynamicTable into the
NWB behavior processing module.

File layout (from inspection):
    contacts        (N, 2)  int64  — [rat1_vertex_idx, rat2_vertex_idx]
    frames          (N,)    int64  — video frame index for each contact event
    vertex_body_map (6880,) object — body-part label per vertex index,
                                    e.g. b'walker/foot_R'
"""

from pathlib import Path

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.basetemporalalignmentinterface import BaseTemporalAlignmentInterface
from neuroconv.utils import DeepDict


class SkinContactsInterface(BaseTemporalAlignmentInterface):
    """
    Skin-contact event interface for Klibaite 2025 - Rat sessions.

    Reads pairwise vertex-contact events computed from sDANNCE body meshes
    and writes them as a :class:`hdmf.common.DynamicTable` in
    ``nwbfile.processing["behavior"]``.

    Each row is one contact event, identified by a frame index and the two
    touching vertex indices (one per rat).  The corresponding body-part labels
    are resolved from the ``vertex_body_map`` stored in the same file.

    Parameters
    ----------
    contacts_file_path : FilePath
        Path to ``skin_contacts_symmetric.h5``.
    frametimes_file_path : FilePath
        Path to a ``frametimes.npy`` file so frame indices can be converted
        to timestamps (elapsed seconds).
    verbose : bool
    """

    @validate_call
    def __init__(
        self,
        contacts_file_path: FilePath,
        frametimes_file_path: FilePath,
        verbose: bool = False,
    ):
        self.contacts_file_path = Path(contacts_file_path)
        self.frametimes_file_path = Path(frametimes_file_path)
        self.verbose = verbose
        self._timestamps = None
        super().__init__(
            contacts_file_path=contacts_file_path,
            frametimes_file_path=frametimes_file_path,
            verbose=verbose,
        )

    # ------------------------------------------------------------------
    # Temporal alignment interface
    # ------------------------------------------------------------------

    def get_original_timestamps(self) -> np.ndarray:
        """Return per-contact timestamps derived from frame indices."""
        import h5py

        frametimes = np.load(str(self.frametimes_file_path))
        all_ts = frametimes[1]  # elapsed seconds, indexed by 0-based frame number

        with h5py.File(self.contacts_file_path, "r") as f:
            frames = f["frames"][:]  # shape (N,)

        return all_ts[frames]

    def get_timestamps(self) -> np.ndarray:
        if self._timestamps is not None:
            return self._timestamps
        return self.get_original_timestamps()

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.asarray(aligned_timestamps, dtype="float64")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, include only the first 1000 contact events.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        """
        Add a ``SkinContacts`` DynamicTable to the behavior processing module.

        Columns
        -------
        start_time, stop_time : float
            Contact event timestamp (both equal — instantaneous events).
        frame_index : int
            0-based video frame index.
        rat1_vertex : int
            Vertex index on rat1's body mesh.
        rat2_vertex : int
            Vertex index on rat2's body mesh.
        rat1_body_part : str
            Body-part label for rat1's vertex (e.g. ``"walker/foot_R"``).
        rat2_body_part : str
            Body-part label for rat2's vertex.
        """
        import h5py
        from hdmf.common import DynamicTable, VectorData
        from neuroconv.tools.nwb_helpers import get_module

        with h5py.File(self.contacts_file_path, "r") as f:
            contacts = f["contacts"][:]  # (N, 2)
            frames = f["frames"][:]  # (N,)
            vertex_body_map_raw = f["vertex_body_map"][:]  # (6880,) object

        # Decode body-part labels (stored as bytes).
        vertex_body_map = np.array([v.decode("utf-8") if isinstance(v, bytes) else str(v) for v in vertex_body_map_raw])

        rat1_vertices = contacts[:, 0]
        rat2_vertices = contacts[:, 1]

        if stub_test:
            n = 1000
            frames = frames[:n]
            rat1_vertices = rat1_vertices[:n]
            rat2_vertices = rat2_vertices[:n]

        timestamps = self.get_timestamps()
        if stub_test:
            timestamps = timestamps[:n]

        rat1_body_parts = vertex_body_map[rat1_vertices]
        rat2_body_parts = vertex_body_map[rat2_vertices]

        table = DynamicTable(
            name="SkinContacts",
            description=(
                "Pairwise vertex skin-contact events between two rats, "
                "computed from sDANNCE 3D body meshes.  Each row is one "
                "instantaneous contact event.  Vertex indices reference the "
                "STAC body model (6880 vertices total); body-part labels use "
                "the format 'walker/<part_name>'."
            ),
        )

        table.add_column(name="frame_index", description="0-based video frame index.", data=frames.tolist())
        table.add_column(name="timestamp", description="Elapsed seconds from session start.", data=timestamps.tolist())
        table.add_column(
            name="rat1_vertex", description="Vertex index on rat1's body mesh.", data=rat1_vertices.tolist()
        )
        table.add_column(
            name="rat2_vertex", description="Vertex index on rat2's body mesh.", data=rat2_vertices.tolist()
        )
        table.add_column(
            name="rat1_body_part", description="Body-part label for rat1's vertex.", data=rat1_body_parts.tolist()
        )
        table.add_column(
            name="rat2_body_part", description="Body-part label for rat2's vertex.", data=rat2_body_parts.tolist()
        )

        behavior_module = get_module(nwbfile=nwbfile, name="behavior", description="Processed behavioral data.")
        behavior_module.add(table)
