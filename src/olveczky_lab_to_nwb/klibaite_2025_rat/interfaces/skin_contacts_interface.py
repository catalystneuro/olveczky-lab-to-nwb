"""
Skin contacts interface for the Klibaite 2025 - Rat social behavior conversion.

Reads ``skin_contacts_symmetric.h5`` and writes the events as a single shared
``pynwb.event.EventsTable`` into ``nwbfile.events``, via ``BaseEventsInterface``.
Each unique ``(rat1_body_part, rat2_body_part)`` pair is one event type,
discriminated by the table's ``event_type`` column.

File layout (from inspection):
    contacts        (N, 2)  int64  — [rat1_vertex_idx, rat2_vertex_idx]
    frames          (N,)    int64  — video frame index for each contact event
    vertex_body_map (6880,) object — body-part label per vertex index,
                                    e.g. b'walker/foot_R'
"""

import copy
from collections import defaultdict
from pathlib import Path

import numpy as np
from pydantic import FilePath, validate_call

from neuroconv.datainterfaces.events.baseeventsinterface import BaseEventsInterface, _EventsData


def _humanize_body_part(raw_body_part: str) -> str:
    """Turn a raw ``vertex_body_map`` label into a human-readable body part name.

    Drops the ``"walker/"`` prefix and expands the ``_R``/``_L`` side suffix, e.g.
    ``"walker/foot_R"`` -> ``"right foot"``, ``"walker/toe_L"`` -> ``"left toe"``,
    ``"walker/jaw"`` -> ``"jaw"``.
    """
    name = raw_body_part.rsplit("/", 1)[-1]
    side = ""
    if name.endswith("_R"):
        side, name = "right ", name[: -len("_R")]
    elif name.endswith("_L"):
        side, name = "left ", name[: -len("_L")]
    return f"{side}{name.replace('_', ' ')}"


class SkinContactsInterface(BaseEventsInterface):
    """
    Skin-contact event interface for Klibaite 2025 - Rat sessions.

    Reads pairwise vertex-contact events computed from sDANNCE body meshes and writes them into a
    single shared ``SkinContacts`` ``EventsTable`` (one row per contact occurrence) in
    ``nwbfile.events``. Each unique ``(rat1_body_part, rat2_body_part)`` pair is one
    event type, named ``"<rat1_body_part> x <rat2_body_part>"`` and recorded in the table's
    ``event_type`` discriminator column; ``frame_index``, ``rat1_vertex``, and ``rat2_vertex`` columns
    carry the per-occurrence detail.

    Parameters
    ----------
    contacts_file_path : FilePath
        Path to ``skin_contacts_symmetric.h5``.
    frametimes_file_path : FilePath
        Path to a ``frametimes.npy`` file so frame indices can be converted to timestamps (elapsed
        seconds).
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
        self._timestamps = None
        self._stub_test = False
        super().__init__(
            contacts_file_path=contacts_file_path,
            frametimes_file_path=frametimes_file_path,
            verbose=verbose,
        )
        self.metadata_key = "skin_contacts"

    # ------------------------------------------------------------------
    # Temporal alignment
    # ------------------------------------------------------------------

    def get_original_timestamps(self) -> np.ndarray:
        """Return per-contact timestamps derived from frame indices."""
        import h5py

        frametimes = np.load(str(self.frametimes_file_path))
        all_ts = frametimes[1]  # elapsed seconds, indexed by 0-based frame number

        with h5py.File(self.contacts_file_path, "r") as f:
            frames: np.ndarray = np.asarray(f["frames"])  # shape (N,)

        return all_ts[frames]

    def get_timestamps(self) -> np.ndarray:
        if self._timestamps is not None:
            return self._timestamps
        return self.get_original_timestamps()

    def set_aligned_timestamps(self, aligned_timestamps: np.ndarray) -> None:
        self._timestamps = np.asarray(aligned_timestamps, dtype="float64")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _get_events_data_dict(self) -> dict[str, _EventsData]:
        if self._events_data_dict is not None:
            return self._events_data_dict

        import h5py

        with h5py.File(self.contacts_file_path, "r") as f:
            contacts: np.ndarray = np.asarray(f["contacts"])  # (N, 2)
            frames: np.ndarray = np.asarray(f["frames"])  # (N,)
            vertex_body_map_raw: np.ndarray = np.asarray(f["vertex_body_map"])  # (6880,) object

        vertex_body_map = np.array([v.decode("utf-8") if isinstance(v, bytes) else str(v) for v in vertex_body_map_raw])
        rat1_vertices = contacts[:, 0]
        rat2_vertices = contacts[:, 1]
        timestamps = self.get_timestamps()

        if self._stub_test:
            n = 1000
            frames = frames[:n]
            rat1_vertices = rat1_vertices[:n]
            rat2_vertices = rat2_vertices[:n]
            timestamps = timestamps[:n]

        rat1_body_parts = vertex_body_map[rat1_vertices]
        rat2_body_parts = vertex_body_map[rat2_vertices]

        # Group per-occurrence data by (rat1_body_part, rat2_body_part) contact type.
        groups: dict[str, dict] = defaultdict(
            lambda: {"timestamps": [], "frame_index": [], "rat1_vertex": [], "rat2_vertex": []}
        )
        for i in range(len(timestamps)):
            event_type_source_id = f"{rat1_body_parts[i]} x {rat2_body_parts[i]}"
            group = groups[event_type_source_id]
            group["timestamps"].append(float(timestamps[i]))
            group["frame_index"].append(int(frames[i]))
            group["rat1_vertex"].append(int(rat1_vertices[i]))
            group["rat2_vertex"].append(int(rat2_vertices[i]))

        self._events_data_dict = {
            event_type_source_id: _EventsData(
                event_type_source_id=event_type_source_id,
                timestamps=np.asarray(group["timestamps"]),
                payload={
                    "frame_index": np.asarray(group["frame_index"]),
                    "rat1_vertex": np.asarray(group["rat1_vertex"]),
                    "rat2_vertex": np.asarray(group["rat2_vertex"]),
                },
            )
            for event_type_source_id, group in groups.items()
        }
        return self._events_data_dict

    def get_metadata(self):
        metadata = super().get_metadata()

        metadata["Events"]["EventTables"]["skin_contacts"] = {
            "table_name": "SkinContacts",
            "description": (
                "Pairwise body-part skin-contact events between two rats, computed from sDANNCE 3D "
                "body meshes. Vertex indices reference the STAC body model (6880 vertices total); "
                "the 'event_type' column names each contact type as '<rat1 body part> x <rat2 body part>' "
                "(e.g. 'right foot x left toe')."
            ),
        }

        event_types = metadata["Events"][self.metadata_key]["event_types"]
        for event_type_source_id in self._get_events_data_dict():
            raw_rat1_body_part, raw_rat2_body_part = event_type_source_id.split(" x ")
            rat1_body_part = _humanize_body_part(raw_rat1_body_part)
            rat2_body_part = _humanize_body_part(raw_rat2_body_part)
            event_types[event_type_source_id] = {
                "event_name": f"{rat1_body_part} x {rat2_body_part}",
                "event_description": f"Skin contact between rat1's {rat1_body_part} and rat2's {rat2_body_part}.",
                "table_metadata_key": "skin_contacts",
                "columns": {
                    "frame_index": {
                        "column_name": "frame_index",
                        "description": "0-based video frame index of the contact event.",
                    },
                    "rat1_vertex": {
                        "column_name": "rat1_vertex",
                        "description": "Vertex index on rat1's body mesh for the contact event.",
                    },
                    "rat2_vertex": {
                        "column_name": "rat2_vertex",
                        "description": "Vertex index on rat2's body mesh for the contact event.",
                    },
                },
            }
        return metadata

    def get_conversion_options_schema(self) -> dict:
        schema = super().get_conversion_options_schema()
        schema["properties"]["stub_test"] = {
            "type": "boolean",
            "default": False,
            "description": "If True, include only the first 1000 contact events.",
        }
        return schema

    def add_to_nwbfile(self, nwbfile, metadata: dict | None = None, stub_test: bool = False) -> None:
        # get_metadata() (built from the full, non-stubbed data) may already have run by the time this
        # is called, e.g. via NWBConverter.get_metadata(). Rebuild this interface's own event_types/
        # EventTables metadata under the requested stub_test so the declared event types always match
        # what _get_events_data_dict() actually produces (a mismatch would KeyError in the writer).
        self._stub_test = stub_test
        self._events_data_dict = None
        own_metadata = self.get_metadata()

        if metadata is None:
            metadata = own_metadata
        else:
            metadata = copy.deepcopy(metadata)
            metadata.setdefault("Events", {})
            metadata["Events"][self.metadata_key] = own_metadata["Events"][self.metadata_key]
            metadata["Events"].setdefault("EventTables", {})
            metadata["Events"]["EventTables"].update(own_metadata["Events"]["EventTables"])

        super().add_to_nwbfile(nwbfile, metadata=metadata)
