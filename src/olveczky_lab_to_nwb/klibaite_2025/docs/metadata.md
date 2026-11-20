# Metadata

The metadata of each NWB file comes from three places:

| Source | Content |
| --- | --- |
| the data files | cameras and their calibration, video frame times, pose, skin contacts (read by the interfaces) |
| `general_metadata.yaml` | experiment and session description, institution, lab, experimenters, publication, keywords; the skeleton (`Pose`); the task (`Task`); the HED schema, definitions and body part tags (`HED`); ontology terms (`ExternalResources`) |
| `ugne_rat_log.xlsx` and `utils/subject_metadata.py` | the subject: ID, sex, strain, genotype, date of birth, markings, cage, mother, supplier |

`session_to_nwb` merges `general_metadata.yaml` over the metadata the interfaces read, then sets the session ID,
start time and subject. Most changes need only the YAML file: edit it, convert one session as a stub (see
[Converting sessions](converting_sessions.md)) and check the file.

## Subjects

`get_subject_metadata` in `utils/subject_metadata.py` reads the rat's row from its cohort's sheet of the rat log (see
[Data organization](data_organization.md#rat-log-ugne_rat_logxlsx)). A rat that is not in the sheet stops the
conversion of its file; add the rat to the sheet to convert it. Fields missing from a sheet are left out of the
file.

## Adding a cohort

1. Put the cohort's folders on the share as described in [Data organization](data_organization.md), and its rats in
   a sheet of `ugne_rat_log.xlsx`.
2. Add the cohort to `COHORTS` in `utils/subject_metadata.py`: its sheet name, strain designation, supplier and, for
   a knockout line, the targeted gene.
3. Add the strain's RRID under `ExternalResources: strain` in `general_metadata.yaml`, keyed by the same strain
   designation. Look it up on [SciCrunch](https://scicrunch.org/) or the
   [Rat Genome Database](https://rgd.mcw.edu).
4. Add the cohort to the experiment description and the cohort table of [Data organization](data_organization.md).
5. Convert one session as a stub and inspect it.

## Skeleton

`Pose: Skeletons: PoseEstimationSDANNCE` lists the 23 landmark names, in the order of the prediction files, and the
skeleton edges as pairs of landmark indices (0-based, from `rat23.mat` of Label3D). The landmark names are also the
keys of the skeleton ontology terms below. `Pose: MultiCameraPoseEstimations` sets the name, software and
description of the pose container.

## HED

[HED](https://www.hedtags.org/) (Hierarchical Event Descriptors) annotates the task and the skin contact types with
tags from a controlled vocabulary, so that they can be searched and compared across datasets. The `HED` section of
`general_metadata.yaml` holds:

- `hed_schema_version`: the HED schema, 8.5.0;
- `definitions`: the lab's definitions. `Social-encounter` describes the task: two awake animals, rat1 and rat2, both
  participants, indoors. `Skin-contact` describes a contact: an agent action of touch;
- `body_parts`: the HED tag of each body part of the skin contact mesh. Keys are patterns, matched in order, so
  `vertebra_C*` (caudal vertebrae, the tail) comes before `vertebra_*` (lumbar vertebrae, the lower back).

The task row carries `Def/Social-encounter` (`Task: hed`). Each contact type carries the definition and the body part
of each rat, for example for `right foot x left toe`:

```text
Def/Skin-contact, (Label/rat1, (Right, Foot)), (Label/rat2, (Left, Toe))
```

HED has no tail or jaw tag, so `Body-part/Tail` and `Face-part/Jaw` extend the schema; HED validation reports
extensions as warnings, not errors. A body part of a new mesh without an entry in `body_parts` stops the conversion
with an error naming it.

`inspection.py` validates the HED of each file with ndx-hed's `HedNWBValidator` (the `hed_errors` column of the
inspection summary). To validate one file by hand:

```python
from ndx_hed.utils.hed_nwb_validator import HedNWBValidator
from pynwb import NWBHDF5IO

with NWBHDF5IO("<file>.nwb", "r") as io:
    nwbfile = io.read()
    validator = HedNWBValidator(nwbfile.lab_meta_data["hed_schema"])
    issues = validator.validate_vector(nwbfile.processing["tasks"]["task_table"]["HED"])
    issues += validator.validate_table(nwbfile.events["SkinContacts"], assemble=False)
```

An empty `issues` list means the annotations are valid. Tags can be looked up in the
[HED schema browser](https://www.hedtags.org/hed-schema-browser/).

## Ontology terms

`ExternalResources` in `general_metadata.yaml` maps values of the files to ontology terms, which NeuroConv writes into
each NWB file as HERD references (the `herd_references` column of the inspection summary counts them, 28 per file).
Each map is keyed by the exact string it annotates; a term for a value that a file does not have is skipped.

| Map | NWB field | Value | Term |
| --- | --- | --- | --- |
| `species` | `Subject.species` | `Rattus norvegicus` | NCBITaxon:10116 |
| `strain` | `Subject.strain` | one strain per cohort | RRID of the Rat Genome Database |
| `experimenter` | `NWBFile.experimenter` | `Klibaite, Ugne`, `Aldarondo, Diego` | ORCID iD |
| `institution` | `NWBFile.institution` | `Harvard University` | ror:03vek6s52 |
| `anatomical_structures` | `Skeleton.nodes` | 23 rat23 landmarks | UBERON |

- Experimenters: only those with an ORCID iD that lists an Olveczky lab paper. Add the others' iDs when known.
- Skeleton: UBERON has no left and right terms, so both sides of a paired landmark share one term, written once with
  a YAML anchor. The three spine points map to the vertebral column and `TailBase` to the tail.

A new strain, landmark or experimenter needs an entry with exactly the same spelling. Look up terms in the
[EBI Ontology Lookup Service](https://www.ebi.ac.uk/ols4) (UBERON, NCBITaxon), [SciCrunch](https://scicrunch.org/)
(RRID), [ORCID](https://orcid.org) and [ROR](https://ror.org).
