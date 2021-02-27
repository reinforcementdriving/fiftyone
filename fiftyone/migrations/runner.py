"""
FiftyOne migrations runner.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import bisect
import logging
import os
from packaging.version import Version

import eta.core.serial as etas
import eta.core.utils as etau

import fiftyone as fo
import fiftyone.constants as foc
import fiftyone.core.odm as foo


logger = logging.getLogger(__name__)


DOWN = "down"
UP = "up"


def _migrations_disabled():
    return os.environ.get("FIFTYONE_DISABLE_MIGRATIONS", "0") != "0"


def get_database_revision():
    """Gets the current revision of the database.

    Returns:
        the database revision string
    """
    config = _get_database_config()
    return config.version


def get_dataset_revision(name):
    """Gets the current revision of the given dataset.

    Args:
        name: the name of the dataset

    Returns:
        the dataset revision string
    """
    conn = foo.get_db_conn()
    dataset_doc = conn.datasets.find_one({"name": name})
    if dataset_doc is None:
        raise ValueError("Dataset '%s' not found" % name)

    return dataset_doc.get("version", None)


def migrate_all(destination=None, verbose=False):
    """Migrates the database and all datasets to the specified destination
    revision.

    Args:
        destination (None): the destination revision. By default, the
            ``fiftyone`` package version is used
        verbose (False): whether to log incremental migrations that are run
    """
    if destination is None:
        destination = foc.VERSION

    migrate_database_if_necessary(destination=destination, verbose=verbose)

    for name in fo.list_datasets():
        migrate_dataset_if_necessary(
            name, destination=destination, verbose=verbose
        )


def migrate_database_if_necessary(destination=None, verbose=False):
    """Migrates the database to the current revision of the ``fiftyone``
    package, if necessary.

    Args:
        destination (None): the destination revision. By default, the
            ``fiftyone`` package version is used
        verbose (False): whether to log incremental migrations that are run
    """
    if _migrations_disabled():
        return

    if destination is None:
        destination = foc.VERSION

    config = _get_database_config()

    head = config.version
    if head is None:
        head = "0.0"  # < v0.7.1

    if head == destination:
        return

    if _database_exists():
        runner = MigrationRunner(head=head, destination=destination)
        if runner.has_admin_revisions:
            logger.info("Migrating database to v%s", destination)
            runner.run_admin(verbose=verbose)

    config_path = _get_database_config_path()
    if Version(destination) >= Version("0.7.1"):
        config.version = destination
        config.write_json(config_path)
    elif os.path.isfile(config_path):
        # Old version of FiftyOne that didn't have DB config files
        os.remove(config_path)


def migrate_dataset_if_necessary(name, destination=None, verbose=False):
    """Migrates the dataset from its current revision to the specified
    destination revision.

    Args:
        name: the name of the dataset
        destination (None): the destination revision. By default, the
            ``fiftyone`` package version is used
        verbose (False): whether to log incremental migrations that are run
    """
    if _migrations_disabled():
        return

    if destination is None:
        destination = foc.VERSION

    head = get_dataset_revision(name)
    if head is None:
        head = "0.0"  # < v0.6.2

    if head == destination:
        return

    runner = MigrationRunner(head=head, destination=destination)
    if runner.has_revisions:
        logger.info("Migrating dataset '%s' to v%s", name, destination)
        runner.run(name, verbose=verbose)

    if Version(destination) >= Version("0.6.2"):
        conn = foo.get_db_conn()
        dataset_doc = conn.datasets.update_one(
            {"name": name}, {"$set": {"version": destination}}
        )
    else:
        # Old version of FiftyOne that didn't store dataset versions
        pass


class MigrationRunner(object):
    """Class for running FiftyOne migrations.

    Args:
        head (None): the current revision
        destination (None): the destination revision
    """

    def __init__(
        self,
        head=None,
        destination=None,
        _revisions=None,
        _admin_revisions=None,
    ):
        if head is None:
            head = foc.VERSION

        if destination is None:
            destination = foc.VERSION

        if _revisions is None:
            _revisions = _get_all_revisions()

        if _admin_revisions is None:
            _admin_revisions = _get_all_revisions(admin=True)

        self._head = head
        self._destination = destination
        self._revisions, self._direction = _get_revisions_to_run(
            head, destination, _revisions
        )
        self._admin_revisions, _ = _get_revisions_to_run(
            head, destination, _admin_revisions
        )

    @property
    def head(self):
        """The head revision."""
        return self._head

    @property
    def destination(self):
        """The destination revision."""
        return self._destination

    @property
    def direction(self):
        """The direction of the migration runner; one of ``("up", "down").``"""
        return self._direction

    @property
    def has_revisions(self):
        """Whether there are any revisions to run."""
        return bool(self._revisions)

    @property
    def has_admin_revisions(self):
        """Whether there are any admin revisions to run."""
        return bool(self._admin_revisions)

    @property
    def revisions(self):
        """The list of revisions that will be run by :meth:`run`."""
        return [r[0] for r in self._revisions]

    @property
    def admin_revisions(self):
        """The list of admin revisions that will be run by :meth:`run_admin`.
        """
        return [r[0] for r in self._admin_revisions]

    def run(self, dataset_name, verbose=False):
        """Runs any required migrations on the specified dataset.

        Args:
            dataset_name: the name of the dataset to migrate
            verbose (False): whether to log incremental migrations that are run
        """
        conn = foo.get_db_conn()
        for rev, module in self._revisions:
            if verbose:
                logger.info("Running v%s %s migration", rev, self.direction)

            fcn = etau.get_function(self.direction, module)
            fcn(conn, dataset_name)

    def run_admin(self, verbose=False):
        """Runs any required admin revisions.

        Args:
            verbose (False): whether to log incremental migrations that are run
        """
        client = foo.get_db_client()
        for rev, module in self._admin_revisions:
            if verbose:
                logger.info(
                    "Running v%s %s admin migration", rev, self.direction
                )

            fcn = etau.get_function(self.direction, module)
            fcn(client)


class DatabaseConfig(etas.Serializable):
    """Config for the database's state.

    Args:
        version (None): the ``fiftyone`` package version for which the database
            is configured
    """

    def __init__(self, version=None):
        self.version = version

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


def _database_exists():
    client = foo.get_db_client()
    return foc.DEFAULT_DATABASE in client.list_database_names()


def _get_database_config():
    try:
        config_path = _get_database_config_path()
        config = DatabaseConfig.from_json(config_path)
    except FileNotFoundError:
        config = DatabaseConfig()

    return config


def _get_database_config_path():
    return os.path.join(fo.config.database_dir, "config.json")


def _get_revisions_to_run(head, dest, revisions):
    revisions = sorted(revisions, key=lambda r: Version(r[0]))

    head = Version(head)
    dest = Version(dest)

    rev_versions = [Version(r[0]) for r in revisions]

    head_idx = bisect.bisect(rev_versions, head)
    dest_idx = bisect.bisect(rev_versions, dest)

    if dest >= head:
        revisions_to_run = revisions[head_idx:dest_idx]
        return revisions_to_run, UP

    revisions_to_run = revisions[dest_idx:head_idx][::-1]
    return revisions_to_run, DOWN


def _get_all_revisions(admin=False):
    revisions_dir = foc.MIGRATIONS_REVISIONS_DIR
    if admin:
        revisions_dir = os.path.join(revisions_dir, "admin")

    revision_files = [
        f for f in etau.list_files(revisions_dir) if f.endswith(".py")
    ]

    module_prefix = __loader__.name.rsplit(".", 1)[0] + ".revisions"
    if admin:
        module_prefix = module_prefix + ".admin"

    revisions = []
    for filename in revision_files:
        version = filename[1:-3].replace("_", ".")
        module = module_prefix + "." + filename[:-3]
        revisions.append((version, module))

    return sorted(revisions, key=lambda r: Version(r[0]))
