"""Interface for the skin contacts between the two rats of a session (skin_contacts_symmetric.h5)."""

import fnmatch
from pathlib import Path

import h5py
import numpy as np
from hdmf.common import MeaningsTable, VectorData
from ndx_hed import HedTags
from neuroconv.basedatainterface import BaseDataInterface
from pydantic import FilePath
from pynwb.event import EventsTable, TimestampVectorData
from pynwb.file import NWBFile

# Number of contacts written in stub mode.
_STUB_CONTACTS = 1000


def parse_body_part(raw_body_part: str) -> tuple[str, str]:
    """Split a body part label of the mesh into its name and side.

    "walker/foot_R" gives ("foot", "right"), "walker/jaw" gives ("jaw", "").
    """
    name = raw_body_part.removeprefix("walker/")
    for suffix, side in (("_L", "left"), ("_R", "right")):
        if name.endswith(suffix):
            return name.removesuffix(suffix), side
    return name, ""


class SkinContactsInterface(BaseDataInterface):
    """Write the skin contacts between the two rats of a session to an ``EventsTable`` in ``nwbfile.events``.

    ``skin_contacts_symmetric.h5`` holds one row per contact: ``contacts`` (the vertex of rat1's and of
    rat2's body mesh that touch), ``frames`` (the video frame of the contact) and ``vertex_body_map`` (the
    body part of each of the 6880 vertices of the STAC body mesh). Each contact becomes one row of the
    ``SkinContacts`` table, timed by Camera1's ``frametimes.npy`` at its frame, with the columns
    ``event_type`` ("<rat1 body part> x <rat2 body part>", e.g. "right foot x left toe"), ``frame_index``,
    ``rat1_vertex`` and ``rat2_vertex``. A meanings table describes each event type and annotates it with
    HED, from ``metadata["HED"]["body_parts"]`` (see ``general_metadata.yaml``).

    The file is the same for both rats of the session, so both NWB files hold the same table.
    """

    keywords = ["skin contacts", "social behavior", "events", "HED"]

    def __init__(self, contacts_file_path: FilePath, frametimes_file_path: FilePath, verbose: bool = False):
        """
        Parameters
        ----------
        contacts_file_path : FilePath
            Path to ``skin_contacts_symmetric.h5``.
        frametimes_file_path : FilePath
            Path to Camera1's ``frametimes.npy`` (row 1: the time of each frame, in seconds).
        verbose : bool, default: False
        """
        self.verbose = verbose
        super().__init__(contacts_file_path=contacts_file_path, frametimes_file_path=frametimes_file_path)

    def add_to_nwbfile(self, nwbfile: NWBFile, metadata: dict, stub_test: bool = False) -> None:
        with h5py.File(self.source_data["contacts_file_path"], "r") as file:
            contacts = file["contacts"][:]
            frames = file["frames"][:]
            vertex_body_map = file["vertex_body_map"][:].astype(str)
        frame_times = np.load(Path(self.source_data["frametimes_file_path"]))[1]

        # Look up the body part of each contact through small integer codes, so that the event type
        # strings are built once per body part pair and not once per contact.
        body_parts, vertex_codes = np.unique(vertex_body_map, return_inverse=True)
        pair_codes = vertex_codes[contacts[:, 0]] * len(body_parts) + vertex_codes[contacts[:, 1]]

        order = np.argsort(frames, kind="stable")
        if stub_test:
            order = order[:_STUB_CONTACTS]
        frames, contacts, pair_codes = frames[order], contacts[order], pair_codes[order]
        used_pair_codes, pair_index = np.unique(pair_codes, return_inverse=True)

        event_names, meanings, hed_strings = [], [], []
        for pair_code in used_pair_codes:
            rat1_part, rat1_side = parse_body_part(body_parts[pair_code // len(body_parts)])
            rat2_part, rat2_side = parse_body_part(body_parts[pair_code % len(body_parts)])
            rat1_name = f"{rat1_side} {rat1_part.replace('_', ' ')}".strip()
            rat2_name = f"{rat2_side} {rat2_part.replace('_', ' ')}".strip()
            event_names.append(f"{rat1_name} x {rat2_name}")
            meanings.append(f"Skin contact between rat1's {rat1_name} and rat2's {rat2_name}.")
            hed_strings.append(
                f"Def/Skin-contact, {self._get_hed_body_part('rat1', rat1_part, rat1_side, metadata)}, "
                f"{self._get_hed_body_part('rat2', rat2_part, rat2_side, metadata)}"
            )

        table = EventsTable(
            name="SkinContacts",
            description=(
                "Skin contacts between the two rats, computed from their sDANNCE 3D body meshes. One row per pair "
                "of touching vertices and video frame. Vertex indices refer to the STAC body mesh (6880 vertices)."
            ),
            columns=[
                TimestampVectorData(name="timestamp", description="Time of the contact.", data=frame_times[frames]),
                VectorData(
                    name="event_type",
                    description="Contact type, '<rat1 body part> x <rat2 body part>'.",
                    data=np.array(event_names, dtype=object)[pair_index],
                ),
                VectorData(name="frame_index", description="0-based video frame of the contact.", data=frames),
                VectorData(name="rat1_vertex", description="Vertex of rat1's body mesh.", data=contacts[:, 0]),
                VectorData(name="rat2_vertex", description="Vertex of rat2's body mesh.", data=contacts[:, 1]),
            ],
        )
        table.add_meanings_table(
            MeaningsTable(
                target=table["event_type"],
                description="Meaning of each contact type, with its HED annotation.",
                columns=[
                    VectorData(name="value", description="The contact type.", data=event_names),
                    VectorData(name="meaning", description="Meaning of the contact type.", data=meanings),
                    HedTags(description="HED annotation of the contact type.", data=hed_strings),
                ],
            )
        )
        nwbfile.add_events_table(table)

    @staticmethod
    def _get_hed_body_part(rat: str, body_part: str, side: str, metadata: dict) -> str:
        """HED group of one rat's body part, e.g. "(Label/rat1, (Right, Foot))"."""
        hed_tag = next(
            (tag for pattern, tag in metadata["HED"]["body_parts"].items() if fnmatch.fnmatchcase(body_part, pattern)),
            None,
        )
        if hed_tag is None:
            raise KeyError(f"Body part {body_part!r} has no HED tag under HED.body_parts in general_metadata.yaml.")
        return f"(Label/{rat}, ({side.capitalize()}, {hed_tag}))" if side else f"(Label/{rat}, {hed_tag})"
