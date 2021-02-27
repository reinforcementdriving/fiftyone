"""
Evaluation runs framework.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from fiftyone.core.runs import Run, RunInfo, RunConfig


class EvaluationInfo(RunInfo):
    """Information about an evaluation that has been run on a dataset.

    Args:
        key: the evaluation key
        timestamp (None): the UTC ``datetime`` when the evaluation was run
        config (None): the :class:`EvaluationMethodConfig` for the evaluation
    """

    @classmethod
    def config_cls(cls):
        return EvaluationMethodConfig


class EvaluationMethodConfig(RunConfig):
    """Base class for configuring :class:`EvaluationMethod` instances.

    Args:
        **kwargs: any leftover keyword arguments after subclasses have done
            their parsing
    """

    pass


class EvaluationMethod(Run):
    """Base class for evaluation methods.

    Subclasses will typically declare an interface method that handles
    performing evaluation on an image, video, or entire collection.

    Args:
        config: an :class:`EvaluationMethodConfig`
    """

    @classmethod
    def run_info_cls(cls):
        return EvaluationInfo

    @classmethod
    def _runs_field(cls):
        return "evaluations"

    @classmethod
    def _run_str(cls):
        return "evaluation"


class EvaluationResults(object):
    """Base class for evaluation results."""

    pass
