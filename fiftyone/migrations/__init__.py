"""
FiftyOne's migration interface.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from .runner import (
    get_database_revision,
    get_dataset_revision,
    migrate_all,
    migrate_database_if_necessary,
    migrate_dataset_if_necessary,
)
