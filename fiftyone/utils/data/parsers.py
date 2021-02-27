"""
Sample parsers.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
import numpy as np

import eta.core.image as etai
import eta.core.frames as etaf
import eta.core.serial as etas
import eta.core.utils as etau
import eta.core.video as etav

import fiftyone.core.eta_utils as foe
import fiftyone.core.labels as fol
import fiftyone.core.metadata as fom
import fiftyone.core.sample as fos


def add_images(dataset, samples, sample_parser, tags=None):
    """Adds the given images to the dataset.

    This operation does not read the images.

    See :ref:`this guide <custom-sample-parser>` for more details about
    adding images to a dataset by defining your own
    :class:`UnlabeledImageSampleParser <fiftyone.utils.data.parsers.UnlabeledImageSampleParser>`.

    Args:
        dataset: a :class:`fiftyone.core.dataset.Dataset`
        samples: an iterable of samples
        sample_parser: a
            :class:`fiftyone.utils.data.parsers.UnlabeledImageSampleParser`
            instance to use to parse the samples
        tags (None): an optional list of tags to attach to each sample

    Returns:
        a list of IDs of the samples that were added to the dataset
    """
    if not sample_parser.has_image_path:
        raise ValueError(
            "Sample parser must have `has_image_path == True` to add its "
            "samples to the dataset"
        )

    if not isinstance(sample_parser, UnlabeledImageSampleParser):
        raise ValueError(
            "`sample_parser` must be a subclass of %s; found %s"
            % (
                etau.get_class_name(UnlabeledImageSampleParser),
                etau.get_class_name(sample_parser),
            )
        )

    def parse_sample(sample):
        sample_parser.with_sample(sample)

        image_path = sample_parser.get_image_path()

        if sample_parser.has_image_metadata:
            metadata = sample_parser.get_image_metadata()
        else:
            metadata = None

        return fos.Sample(filepath=image_path, metadata=metadata, tags=tags)

    try:
        num_samples = len(samples)
    except:
        num_samples = None

    _samples = map(parse_sample, samples)
    return dataset.add_samples(
        _samples, num_samples=num_samples, expand_schema=False
    )


def add_labeled_images(
    dataset,
    samples,
    sample_parser,
    label_field="ground_truth",
    tags=None,
    expand_schema=True,
):
    """Adds the given labeled images to the dataset.

    This operation will iterate over all provided samples, but the images will
    not be read (unless the sample parser requires it in order to compute image
    metadata).

    See :ref:`this guide <custom-sample-parser>` for more details about
    adding labeled images to a dataset by defining your own
    :class:`LabeledImageSampleParser <fiftyone.utils.data.parsers.LabeledImageSampleParser>`.

    Args:
        dataset: a :class:`fiftyone.core.dataset.Dataset`
        samples: an iterable of samples
        sample_parser: a
            :class:`fiftyone.utils.data.parsers.LabeledImageSampleParser`
            instance to use to parse the samples
        label_field ("ground_truth"): the name (or root name) of the field(s)
            to use for the labels
        tags (None): an optional list of tags to attach to each sample
        expand_schema (True): whether to dynamically add new sample fields
            encountered to the dataset schema. If False, an error is raised
            if a sample's schema is not a subset of the dataset schema

    Returns:
        a list of IDs of the samples that were added to the dataset
    """
    if not sample_parser.has_image_path:
        raise ValueError(
            "Sample parser must have `has_image_path == True` to add its "
            "samples to the dataset"
        )

    if not isinstance(sample_parser, LabeledImageSampleParser):
        raise ValueError(
            "`sample_parser` must be a subclass of %s; found %s"
            % (
                etau.get_class_name(LabeledImageSampleParser),
                etau.get_class_name(sample_parser),
            )
        )

    # Check if a single label field is being imported
    try:
        single_label_field = issubclass(sample_parser.label_cls, fol.Label)
    except:
        single_label_field = False

    if expand_schema and single_label_field:
        # This has the benefit of ensuring that `label_field` exists, even if
        # all of the parsed samples are unlabeled (i.e., return labels that are
        # all `None`)
        dataset._ensure_label_field(label_field, sample_parser.label_cls)

        # The schema now never needs expanding, because we already ensured
        # that `label_field` exists, if necessary
        expand_schema = False

    if label_field:
        label_key = lambda k: label_field + "_" + k
    else:
        label_key = lambda k: k

    def parse_sample(sample):
        sample_parser.with_sample(sample)

        image_path = sample_parser.get_image_path()

        if sample_parser.has_image_metadata:
            metadata = sample_parser.get_image_metadata()
        else:
            metadata = None

        label = sample_parser.get_label()

        sample = fos.Sample(filepath=image_path, metadata=metadata, tags=tags)

        if isinstance(label, dict):
            sample.update_fields({label_key(k): v for k, v in label.items()})
        elif label is not None:
            sample[label_field] = label

        return sample

    try:
        num_samples = len(samples)
    except:
        num_samples = None

    _samples = map(parse_sample, samples)
    return dataset.add_samples(
        _samples, expand_schema=expand_schema, num_samples=num_samples
    )


def add_videos(dataset, samples, sample_parser, tags=None):
    """Adds the given videos to the dataset.

    This operation does not read the videos.

    See :ref:`this guide <custom-sample-parser>` for more details about
    adding videos to a dataset by defining your own
    :class:`UnlabeledVideoSampleParser <fiftyone.utils.data.parsers.UnlabeledVideoSampleParser>`.

    Args:
        dataset: a :class:`fiftyone.core.dataset.Dataset`
        samples: an iterable of samples
        sample_parser: a
            :class:`fiftyone.utils.data.parsers.UnlabeledVideoSampleParser`
            instance to use to parse the samples
        tags (None): an optional list of tags to attach to each sample

    Returns:
        a list of IDs of the samples that were added to the dataset
    """
    if not isinstance(sample_parser, UnlabeledVideoSampleParser):
        raise ValueError(
            "`sample_parser` must be a subclass of %s; found %s"
            % (
                etau.get_class_name(UnlabeledVideoSampleParser),
                etau.get_class_name(sample_parser),
            )
        )

    def parse_sample(sample):
        sample_parser.with_sample(sample)

        video_path = sample_parser.get_video_path()

        if sample_parser.has_video_metadata:
            metadata = sample_parser.get_video_metadata()
        else:
            metadata = None

        return fos.Sample(filepath=video_path, metadata=metadata, tags=tags)

    try:
        num_samples = len(samples)
    except:
        num_samples = None

    _samples = map(parse_sample, samples)

    # @todo: skip schema expansion and set media type before adding samples
    return dataset.add_samples(
        _samples, num_samples=num_samples, expand_schema=True
    )


def add_labeled_videos(
    dataset,
    samples,
    sample_parser,
    label_field="ground_truth",
    tags=None,
    expand_schema=True,
):
    """Adds the given labeled videos to the dataset.

    This operation will iterate over all provided samples, but the videos will
    not be read/decoded/etc.

    See :ref:`this guide <custom-sample-parser>` for more details about
    adding labeled videos to a dataset by defining your own
    :class:`LabeledVideoSampleParser <fiftyone.utils.data.parsers.LabeledVideoSampleParser>`.

    Args:
        dataset: a :class:`fiftyone.core.dataset.Dataset`
        samples: an iterable of samples
        sample_parser: a
            :class:`fiftyone.utils.data.parsers.LabeledVideoSampleParser`
            instance to use to parse the samples
        label_field ("ground_truth"): the name (or root name) of the frame
            fields to use for the labels
        tags (None): an optional list of tags to attach to each sample
        expand_schema (True): whether to dynamically add new sample fields
            encountered to the dataset schema. If False, an error is raised
            if a sample's schema is not a subset of the dataset schema

    Returns:
        a list of IDs of the samples that were added to the dataset
    """
    if not isinstance(sample_parser, LabeledVideoSampleParser):
        raise ValueError(
            "`sample_parser` must be a subclass of %s; found %s"
            % (
                etau.get_class_name(LabeledVideoSampleParser),
                etau.get_class_name(sample_parser),
            )
        )

    if label_field:
        label_key = lambda k: label_field + "_" + k
    else:
        label_key = lambda k: k

    def parse_sample(sample):
        sample_parser.with_sample(sample)

        video_path = sample_parser.get_video_path()

        if sample_parser.has_video_metadata:
            metadata = sample_parser.get_video_metadata()
        else:
            metadata = None

        sample = fos.Sample(filepath=video_path, metadata=metadata, tags=tags)

        frames = sample_parser.get_frame_labels()

        if frames is not None:
            sample.frames.merge(
                {
                    frame_number: {
                        label_key(field_name): label
                        for field_name, label in frame_dict.items()
                    }
                    for frame_number, frame_dict in frames.items()
                }
            )

        return sample

    try:
        num_samples = len(samples)
    except:
        num_samples = None

    _samples = map(parse_sample, samples)
    return dataset.add_samples(
        _samples, expand_schema=expand_schema, num_samples=num_samples
    )


class SampleParser(object):
    """Base interface for sample parsers.

    :class:`SampleParser` instances are used to parse samples emitted by
    dataset iterators when ingesting them into
    :class:`fiftyone.core.dataset.Dataset` instances.

    The general recipe for using :class:`SampleParser` instances is as
    follows::

        sample_parser = SampleParser(...)

        for sample in samples:
            sample_parser.with_sample(sample)
            field = sample_parser.get_<field>()

    where ``field`` is a subclass specific field to parse from the sample.
    """

    def __init__(self):
        self._current_sample = None

    @property
    def current_sample(self):
        """The current sample.

        Raises:
            ValueError: if there is no current sample
        """
        if self._current_sample is None:
            raise ValueError(
                "No current sample. You must call `with_sample()` before "
                "trying to get information about a sample"
            )

        return self._current_sample

    def with_sample(self, sample):
        """Sets the current sample so that subsequent calls to methods of this
        parser will return information from the given sample.

        Guaranteed to call :func:`clear_sample` before setting the current
        sample.

        Args:
            sample: a sample
        """
        self.clear_sample()
        self._current_sample = sample

    def clear_sample(self):
        """Clears the current sample.

        Also clears any cached sample information stored by the parser.
        """
        self._current_sample = None


class UnlabeledImageSampleParser(SampleParser):
    """Interface for :class:`SampleParser` instances that parse unlabeled image
    samples.

    Instances of this class must return images in ``numpy`` format.

    The general recipe for using :class:`UnlabeledImageSampleParser` instances
    is as follows::

        sample_parser = UnlabeledImageSampleParser(...)

        for sample in samples:
            sample_parser.with_sample(sample)
            img = sample_parser.get_image()
            if sample_parser.has_image_path:
                image_path = sample_parser.get_image_path()

            if sample_parser.has_image_metadata:
                image_metadata = sample_parser.get_image_metadata()
    """

    @property
    def has_image_path(self):
        """Whether this parser produces paths to images on disk for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_image_path")

    @property
    def has_image_metadata(self):
        """Whether this parser produces
        :class:`fiftyone.core.metadata.ImageMetadata` instances for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_image_metadata")

    def get_image(self):
        """Returns the image from the current sample.

        Returns:
            a numpy image
        """
        raise NotImplementedError("subclass must implement get_image()")

    def get_image_path(self):
        """Returns the image path for the current sample.

        Returns:
            the path to the image on disk
        """
        if not self.has_image_path:
            raise ValueError(
                "This '%s' does not provide image paths"
                % etau.get_class_name(self)
            )

        raise NotImplementedError("subclass must implement get_image_path()")

    def get_image_metadata(self):
        """Returns the image metadata for the current sample.

        Returns:
            a :class:`fiftyone.core.metadata.ImageMetadata` instance
        """
        if not self.has_image_metadata:
            raise ValueError(
                "This '%s' does not provide image metadata"
                % etau.get_class_name(self)
            )

        raise NotImplementedError(
            "subclass must implement get_image_metadata()"
        )


class UnlabeledVideoSampleParser(SampleParser):
    """Interface for :class:`SampleParser` instances that parse unlabeled video
    samples.

    The general recipe for using :class:`UnlabeledVideoSampleParser` instances
    is as follows::

        sample_parser = UnlabeledVideoSampleParser(...)

        for sample in samples:
            sample_parser.with_sample(sample)
            video_path = sample_parser.get_video_path()
            video_metadata = sample_parser.get_video_metadata()
    """

    @property
    def has_video_metadata(self):
        """Whether this parser produces
        :class:`fiftyone.core.metadata.VideoMetadata` instances for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_video_metadata")

    def get_video_path(self):
        """Returns the video path for the current sample.

        Returns:
            the path to the video on disk
        """
        raise NotImplementedError("subclass must implement get_video_path()")

    def get_video_metadata(self):
        """Returns the video metadata for the current sample.

        Returns:
            a :class:`fiftyone.core.metadata.VideoMetadata` instance
        """
        if not self.has_video_metadata:
            raise ValueError(
                "This '%s' does not provide video metadata"
                % etau.get_class_name(self)
            )

        raise NotImplementedError(
            "subclass must implement get_video_metadata()"
        )


class ImageSampleParser(UnlabeledImageSampleParser):
    """Sample parser that parses unlabeled image samples.

    This implementation assumes that the provided sample is either an image
    that can be converted to numpy format via ``np.asarray()`` or the path
    to an image on disk.
    """

    @property
    def has_image_path(self):
        return True

    @property
    def has_image_metadata(self):
        return False

    def get_image(self):
        image_or_path = self.current_sample
        if etau.is_str(image_or_path):
            return etai.read(image_or_path)

        return np.asarray(image_or_path)

    def get_image_path(self):
        image_or_path = self.current_sample
        if etau.is_str(image_or_path):
            return image_or_path

        raise ValueError(
            "Cannot extract image path from samples that contain images"
        )


class VideoSampleParser(UnlabeledVideoSampleParser):
    """Sample parser that parses unlabeled video samples.

    This implementation assumes that the provided sample is a path to a video
    on disk.
    """

    @property
    def has_video_metadata(self):
        return False

    def get_video_path(self):
        return self.current_sample


class LabeledImageSampleParser(SampleParser):
    """Interface for :class:`SampleParser` instances that parse labeled image
    samples.

    Instances of this class must return images in ``numpy`` format and labels
    as :class:`fiftyone.core.labels.Label` instances.

    The general recipe for using :class:`LabeledImageSampleParser` instances
    is as follows::

        sample_parser = LabeledImageSampleParser(...)

        for sample in samples:
            sample_parser.with_sample(sample)
            img = sample_parser.get_image()
            label = sample_parser.get_label()

            if sample_parser.has_image_path:
                image_path = sample_parser.get_image_path()

            if sample_parser.has_image_metadata:
                image_metadata = sample_parser.get_image_metadata()
    """

    @property
    def has_image_path(self):
        """Whether this parser produces paths to images on disk for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_image_path")

    @property
    def has_image_metadata(self):
        """Whether this parser produces
        :class:`fiftyone.core.metadata.ImageMetadata` instances for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_image_metadata")

    @property
    def label_cls(self):
        """The :class:`fiftyone.core.labels.Label` class(es) returned by this
        parser.

        This can be any of the following:

        -   a :class:`fiftyone.core.labels.Label` class. In this case, the
            parser is guaranteed to return labels of this type
        -   a dict mapping keys to :class:`fiftyone.core.labels.Label` classes.
            In this case, the parser will return label dictionaries with keys
            and value-types specified by this dictionary. Not all keys need be
            present in the imported labels
        -   ``None``. In this case, the parser makes no guarantees about the
            labels that it may return
        """
        raise NotImplementedError("subclass must implement label_cls")

    def get_image(self):
        """Returns the image from the current sample.

        Returns:
            a numpy image
        """
        raise NotImplementedError("subclass must implement get_image()")

    def get_image_path(self):
        """Returns the image path for the current sample.

        Returns:
            the path to the image on disk
        """
        if not self.has_image_path:
            raise ValueError(
                "This '%s' does not provide image paths"
                % etau.get_class_name(self)
            )

        raise NotImplementedError("subclass must implement get_image_path()")

    def get_image_metadata(self):
        """Returns the image metadata for the current sample.

        Returns:
            a :class:`fiftyone.core.metadata.ImageMetadata` instance
        """
        if not self.has_image_metadata:
            raise ValueError(
                "This '%s' does not provide image metadata"
                % etau.get_class_name(self)
            )

        raise NotImplementedError(
            "subclass must implement get_image_metadata()"
        )

    def get_label(self):
        """Returns the label for the current sample.

        Returns:
            a :class:`fiftyone.core.labels.Label` instance, or a dictionary
            mapping field names to :class:`fiftyone.core.labels.Label`
            instances, or ``None`` if the sample is unlabeled
        """
        raise NotImplementedError("subclass must implement get_label()")


class LabeledVideoSampleParser(SampleParser):
    """Interface for :class:`SampleParser` instances that parse labeled video
    samples.

    The general recipe for using :class:`LabeledVideoSampleParser` instances
    is as follows::

        sample_parser = LabeledVideoSampleParser(...)

        for sample in samples:
            sample_parser.with_sample(sample)
            video_path = sample_parser.get_video_path()
            label = sample_parser.get_label()
            frames = sample_parser.get_frame_labels()

            if sample_parser.has_video_metadata:
                video_metadata = sample_parser.get_video_metadata()
    """

    @property
    def has_video_metadata(self):
        """Whether this parser produces
        :class:`fiftyone.core.metadata.VideoMetadata` instances for samples
        that it parses.
        """
        raise NotImplementedError("subclass must implement has_video_metadata")

    @property
    def label_cls(self):
        """The :class:`fiftyone.core.labels.Label` class(es) returned by this
        parser within the sample-level labels that it produces.

        This can be any of the following:

        -   a :class:`fiftyone.core.labels.Label` class. In this case, the
            parser is guaranteed to return sample-level labels of this type
        -   a dict mapping keys to :class:`fiftyone.core.labels.Label` classes.
            In this case, the parser will return sample-level label
            dictionaries with keys and value-types specified by this
            dictionary. Not all keys need be present in the imported labels
        -   ``None``. In this case, the parser makes no guarantees about the
            sample-level labels that it may return
        """
        raise NotImplementedError("subclass must implement label_cls")

    @property
    def frame_labels_cls(self):
        """The :class:`fiftyone.core.labels.Label` class(es) returned by this
        parser within the frame labels that it produces.

        This can be any of the following:

        -   a :class:`fiftyone.core.labels.Label` class. In this case, the
            parser is guaranteed to return frame labels of this type
        -   a dict mapping keys to :class:`fiftyone.core.labels.Label` classes.
            In this case, the parser will return frame label dictionaries with
            keys and value-types specified by this dictionary. Not all keys
            need be present in each frame
        -   ``None``. In this case, the parser makes no guarantees about the
            frame labels that it may return
        """
        raise NotImplementedError("subclass must implement frame_labels_cls")

    def get_video_path(self):
        """Returns the video path for the current sample.

        Returns:
            the path to the video on disk
        """
        raise NotImplementedError("subclass must implement get_video_path()")

    def get_video_metadata(self):
        """Returns the video metadata for the current sample.

        Returns:
            a :class:`fiftyone.core.metadata.ImageMetadata` instance
        """
        if not self.has_video_metadata:
            raise ValueError(
                "This '%s' does not provide video metadata"
                % etau.get_class_name(self)
            )

        raise NotImplementedError(
            "subclass must implement get_video_metadata()"
        )

    def get_label(self):
        """Returns the sample-level labels for the current sample.

        Returns:
            a :class:`fiftyone.core.labels.Label` instance, or a dictionary
            mapping field names to :class:`fiftyone.core.labels.Label`
            instances, or ``None`` if the sample has no sample-level labels
        """
        raise NotImplementedError("subclass must implement get_label()")

    def get_frame_labels(self):
        """Returns the frame labels for the current sample.

        Returns:
            a dictionary mapping frame numbers to dictionaries that map label
            fields to :class:`fiftyone.core.labels.Label` instances for each
            video frame, or ``None`` if the sample has no frame labels
        """
        raise NotImplementedError("subclass must implement get_frame_labels()")


class LabeledImageTupleSampleParser(LabeledImageSampleParser):
    """Generic sample parser that parses samples that are
    ``(image_or_path, label)`` tuples, where:

        - ``image_or_path`` is either an image that can be converted to numpy
          format via ``np.asarray()`` or the path to an image on disk

        - ``label`` is a :class:`fiftyone.core.labels.Label` instance

    This implementation provides a :meth:`_current_image` property that
    caches the image for the current sample, for efficiency in case multiple
    getters require access to the image (e.g., to normalize coordinates,
    compute metadata, etc).

    See the following subclasses of this parser for implementations that parse
    labels for common tasks:

        - Image classification: :class:`ImageClassificationSampleParser`
        - Object detection: :class:`ImageDetectionSampleParser`
        - Multitask image prediction: :class:`ImageLabelsSampleParser`
    """

    def __init__(self):
        super().__init__()
        self._current_image_cache = None

    @property
    def has_image_path(self):
        return True

    @property
    def has_image_metadata(self):
        return False

    @property
    def label_cls(self):
        return None

    def get_image(self):
        return self._current_image

    def get_image_path(self):
        image_or_path = self.current_sample[0]
        if etau.is_str(image_or_path):
            return image_or_path

        raise ValueError(
            "Cannot extract image path from samples that contain images"
        )

    def get_label(self):
        return self.current_sample[1]

    def clear_sample(self):
        super().clear_sample()
        self._current_image_cache = None

    @property
    def _current_image(self):
        if self._current_image_cache is None:
            self._current_image_cache = self._get_image()

        return self._current_image_cache

    def _get_image(self):
        image_or_path = self.current_sample[0]
        return self._parse_image(image_or_path)

    def _parse_image(self, image_or_path):
        if etau.is_str(image_or_path):
            return etai.read(image_or_path)

        return np.asarray(image_or_path)


class ImageClassificationSampleParser(LabeledImageTupleSampleParser):
    """Generic parser for image classification samples whose labels are
    represented as :class:`fiftyone.core.labels.Classification` instances.

    This implementation supports samples that are ``(image_or_path, target)``
    tuples, where:

        - ``image_or_path`` is either an image that can be converted to numpy
          format via ``np.asarray()`` or the path to an image on disk

        - ``target`` is either a class ID (if ``classes`` is provided) or a
          label string. For unlabeled images, ``target`` can be ``None``

    Args:
        classes (None): an optional list of class label strings. If provided,
            it is assumed that ``target`` is a class ID that should be mapped
            to a label string via ``classes[target]``
    """

    def __init__(self, classes=None):
        super().__init__()
        self.classes = classes

    @property
    def label_cls(self):
        return fol.Classification

    def get_label(self):
        """Returns the label for the current sample.

        Args:
            sample: the sample

        Returns:
            a :class:`fiftyone.core.labels.Classification` instance
        """
        target = self.current_sample[1]
        return self._parse_label(target)

    def _parse_label(self, target):
        if target is None:
            return None

        try:
            label = self.classes[target]
        except:
            label = str(target)

        return fol.Classification(label=label)


class ImageDetectionSampleParser(LabeledImageTupleSampleParser):
    """Generic parser for image detection samples whose labels are represented
    as :class:`fiftyone.core.labels.Detections` instances.

    This implementation supports samples that are
    ``(image_or_path, detections_or_path)`` tuples, where:

        - ``image_or_path`` is either an image that can be converted to numpy
          format via ``np.asarray()`` or the path to an image on disk

        - ``detections_or_path`` is either a list of detections in the
          following format::

            [
                {
                    "<label_field>": <label-or-target>,
                    "<bounding_box_field>": [
                        <top-left-x>, <top-left-y>, <width>, <height>
                    ],
                    "<confidence_field>": <optional-confidence>,
                    "<attributes_field>": {
                        <optional-name>: <optional-value>,
                        ...
                    }
                },
                ...
            ]

          or the path to such a file on disk. For unlabeled images,
          ``detections_or_path`` can be ``None``.

          In the above, ``label-or-target`` is either a class ID
          (if ``classes`` is provided) or a label string, and the bounding box
          coordinates can either be relative coordinates in ``[0, 1]``
          (if ``normalized == True``) or absolute pixels coordinates
          (if ``normalized == False``). The confidence and attributes fields
          are optional for each sample.

          The input field names can be configured as necessary when
          instantiating the parser.

    Args:
        label_field ("label"): the name of the object label field in the
            target dicts
        bounding_box_field ("bounding_box"): the name of the bounding box field
            in the target dicts
        confidence_field (None): the name of the optional confidence field in
            the target dicts
        attributes_field (None): the name of the optional attributes field in
            the target dicts
        classes (None): an optional list of class label strings. If provided,
            it is assumed that the ``target`` values are class IDs that should
            be mapped to label strings via ``classes[target]``
        normalized (True): whether the bounding box coordinates are absolute
            pixel coordinates (``False``) or relative coordinates in [0, 1]
            (``True``)
    """

    def __init__(
        self,
        label_field="label",
        bounding_box_field="bounding_box",
        confidence_field=None,
        attributes_field=None,
        classes=None,
        normalized=True,
    ):
        super().__init__()
        self.label_field = label_field
        self.bounding_box_field = bounding_box_field
        self.confidence_field = confidence_field
        self.attributes_field = attributes_field
        self.classes = classes
        self.normalized = normalized

    @property
    def label_cls(self):
        return fol.Detections

    def get_label(self):
        """Returns the label for the current sample.

        Returns:
            a :class:`fiftyone.core.labels.Detections` instance
        """
        target = self.current_sample[1]

        if not self.normalized:
            # Absolute bounding box coordinates were provided, so we must have
            # the image to convert to relative coordinates
            img = self._current_image
        else:
            img = None

        return self._parse_label(target, img=img)

    def _parse_label(self, target, img=None):
        if target is None:
            return None

        if etau.is_str(target):
            target = etas.load_json(target)

        return fol.Detections(
            detections=[self._parse_detection(obj, img=img) for obj in target]
        )

    def _parse_detection(self, obj, img=None):
        label = obj[self.label_field]

        try:
            label = self.classes[label]
        except:
            label = str(label)

        tlx, tly, w, h = self._parse_bbox(obj)

        if not self.normalized:
            height, width = img.shape[:2]
            tlx /= width
            tly /= height
            w /= width
            h /= height

        bounding_box = [tlx, tly, w, h]

        if self.confidence_field:
            confidence = obj.get(self.confidence_field, None)
        else:
            confidence = None

        if self.attributes_field:
            _attrs = obj.get(self.attributes_field, {})
            attributes = {
                k: self._parse_attribute(v) for k, v in _attrs.items()
            }
        else:
            attributes = None

        detection = fol.Detection(
            label=label,
            bounding_box=bounding_box,
            confidence=confidence,
            attributes=attributes,
        )

        return detection

    def _parse_bbox(self, obj):
        return obj[self.bounding_box_field]

    def _parse_attribute(self, value):
        if etau.is_str(value):
            return fol.CategoricalAttribute(value=value)

        if isinstance(value, bool):
            return fol.BooleanAttribute(value=value)

        if etau.is_numeric(value):
            return fol.NumericAttribute(value=value)

        return fol.Attribute(value=value)


class ImageLabelsSampleParser(LabeledImageTupleSampleParser):
    """Generic parser for multitask image prediction samples whose labels are
    stored in ``eta.core.image.ImageLabels`` format.

    This implementation provided by this class supports samples that are
    ``(image_or_path, image_labels_or_path)`` tuples, where:

        - ``image_or_path`` is either an image that can be converted to numpy
          format via ``np.asarray()`` or the path to an image on disk

        - ``image_labels_or_path`` is an ``eta.core.image.ImageLabels``
          instance, an ``eta.core.frames.FrameLabels`` instance, a serialized
          dict representation of either, or the path to either on disk

    Args:
        prefix (None): a string prefix to prepend to each label name in the
            expanded label dictionary
        labels_dict (None): a dictionary mapping names of attributes/objects
            in the image labels to field names into which to expand them
        multilabel (False): whether to store frame attributes in a single
            :class:`fiftyone.core.labels.Classifications` instance
        skip_non_categorical (False): whether to skip non-categorical frame
            attributes (True) or cast them to strings (False)
    """

    def __init__(
        self,
        prefix=None,
        labels_dict=None,
        multilabel=False,
        skip_non_categorical=False,
    ):
        super().__init__()
        self.prefix = prefix
        self.labels_dict = labels_dict
        self.multilabel = multilabel
        self.skip_non_categorical = skip_non_categorical

    @property
    def label_cls(self):
        return None

    def get_label(self):
        """Returns the label for the current sample.

        Returns:
            a labels dictionary
        """
        labels = self.current_sample[1]
        return self._parse_label(labels)

    def _parse_label(self, labels):
        return foe.load_image_labels(
            labels,
            prefix=self.prefix,
            labels_dict=self.labels_dict,
            multilabel=self.multilabel,
            skip_non_categorical=self.skip_non_categorical,
        )


class FiftyOneImageClassificationSampleParser(ImageClassificationSampleParser):
    """Parser for samples in FiftyOne image classification datasets.

    See :class:`fiftyone.types.dataset_types.FiftyOneImageClassificationDataset`
    for format details.

    Args:
        classes (None): an optional list of class label strings. If provided,
            it is assumed that ``target`` is a class ID that should be mapped
            to a label string via ``classes[target]``
    """

    def __init__(self, classes=None):
        super().__init__(classes=classes)


class FiftyOneImageDetectionSampleParser(ImageDetectionSampleParser):
    """Parser for samples in FiftyOne image detection datasets.

    See :class:`fiftyone.types.dataset_types.FiftyOneImageDetectionDataset` for
    format details.

    Args:
        classes (None): an optional list of class label strings. If provided,
            it is assumed that the ``target`` values are class IDs that should
            be mapped to label strings via ``classes[target]``
    """

    def __init__(self, classes=None):
        super().__init__(
            label_field="label",
            bounding_box_field="bounding_box",
            confidence_field="confidence",
            attributes_field="attributes",
            classes=classes,
            normalized=True,
        )


class FiftyOneImageLabelsSampleParser(ImageLabelsSampleParser):
    """Parser for samples in FiftyOne image labels datasets.

    See :class:`fiftyone.types.dataset_types.FiftyOneImageLabelsDataset` for
    format details.

    Args:
        prefix (None): a string prefix to prepend to each label name in the
            expanded label dictionary
        labels_dict (None): a dictionary mapping names of attributes/objects
            in the image labels to field names into which to expand them
        multilabel (False): whether to store frame attributes in a single
            :class:`fiftyone.core.labels.Classifications` instance
        skip_non_categorical (False): whether to skip non-categorical frame
            attributes (True) or cast them to strings (False)
    """

    pass


class VideoLabelsSampleParser(LabeledVideoSampleParser):
    """Generic parser for labeled video samples whose labels are represented in
    ``eta.core.video.VideoLabels`` format.

    This implementation provided by this class supports samples that are
    ``(video_path, video_labels_or_path)`` tuples, where:

        - ``video_path`` is the path to a video on disk

        - ``video_labels_or_path`` is an ``eta.core.video.VideoLabels``
          instance, a serialized dict representation of one, or the path to one
          on disk

    Args:
        prefix (None): a string prefix to prepend to each label name in the
            expanded frame label dictionaries
        labels_dict (None): a dictionary mapping names of attributes/objects
            in the frame labels to field names into which to expand them
        multilabel (False): whether to store frame attributes in a single
            :class:`fiftyone.core.labels.Classifications` instance
        skip_non_categorical (False): whether to skip non-categorical frame
            attributes (True) or cast them to strings (False)
    """

    def __init__(
        self,
        prefix=None,
        labels_dict=None,
        multilabel=False,
        skip_non_categorical=False,
    ):
        super().__init__()
        self.prefix = prefix
        self.labels_dict = labels_dict
        self.multilabel = multilabel
        self.skip_non_categorical = skip_non_categorical

    @property
    def has_video_metadata(self):
        return False

    @property
    def label_cls(self):
        return None

    @property
    def frame_labels_cls(self):
        return None

    def get_video_path(self):
        return self.current_sample[0]

    def get_label(self):
        return None

    def get_frame_labels(self):
        labels = self.current_sample[1]
        return self._parse_labels(labels)

    def _parse_labels(self, labels):
        return foe.load_video_labels(
            labels,
            prefix=self.prefix,
            labels_dict=self.labels_dict,
            multilabel=self.multilabel,
            skip_non_categorical=self.skip_non_categorical,
        )


class FiftyOneVideoLabelsSampleParser(VideoLabelsSampleParser):
    """Parser for samples in FiftyOne video labels datasets.

    See :class:`fiftyone.types.dataset_types.FiftyOneVideoLabelsDataset` for
    format details.

    Args:
        expand (True): whether to expand the labels for each frame into
            separate :class:`fiftyone.core.labels.Label` instances
        prefix (None): a string prefix to prepend to each label name in the
            expanded frame label dictionaries
        labels_dict (None): a dictionary mapping names of attributes/objects
            in the frame labels to field names into which to expand them
        multilabel (False): whether to store frame attributes in a single
            :class:`fiftyone.core.labels.Classifications` instance
        skip_non_categorical (False): whether to skip non-categorical frame
            attributes (True) or cast them to strings (False)
    """

    pass


class FiftyOneUnlabeledImageSampleParser(UnlabeledImageSampleParser):
    """Parser for :class:`fiftyone.core.sample.Sample` instances that contain
    images.

    Args:
        compute_metadata (False): whether to compute
            :class:`fiftyone.core.metadata.ImageMetadata` instances on-the-fly
            if :func:`get_image_metadata` is called and no metadata is
            available
    """

    def __init__(self, compute_metadata=False):
        super().__init__()
        self.compute_metadata = compute_metadata

    @property
    def has_image_path(self):
        return True

    @property
    def has_image_metadata(self):
        return True

    def get_image(self):
        return etai.read(self.current_sample.filepath)

    def get_image_path(self):
        return self.current_sample.filepath

    def get_image_metadata(self):
        metadata = self.current_sample.metadata
        if metadata is None and self.compute_metadata:
            metadata = fom.ImageMetadata.build_for(
                self.current_sample.filepath
            )

        return metadata


class FiftyOneLabeledImageSampleParser(LabeledImageSampleParser):
    """Parser for :class:`fiftyone.core.sample.Sample` instances that contain
    labeled images.

    Args:
        label_field_or_dict: the name of the
            :class:`fiftyone.core.labels.Label` field of the samples to parse,
            or a dictionary mapping label field names to keys in the returned
            label dictionary
        compute_metadata (False): whether to compute
            :class:`fiftyone.core.metadata.ImageMetadata` instances on-the-fly
            if :func:`get_image_metadata` is called and no metadata is
            available
    """

    def __init__(self, label_field_or_dict, compute_metadata=False):
        super().__init__()
        self.label_field_or_dict = label_field_or_dict
        self.compute_metadata = compute_metadata

    @property
    def has_image_path(self):
        return True

    @property
    def has_image_metadata(self):
        return True

    @property
    def label_cls(self):
        return None

    def get_image(self):
        return etai.read(self.current_sample.filepath)

    def get_image_path(self):
        return self.current_sample.filepath

    def get_image_metadata(self):
        metadata = self.current_sample.metadata
        if metadata is None and self.compute_metadata:
            metadata = fom.ImageMetadata.build_for(
                self.current_sample.filepath
            )

        return metadata

    def get_label(self):
        if isinstance(self.label_field_or_dict, dict):
            return {
                v: self.current_sample[k]
                for k, v in self.label_field_or_dict.items()
            }

        return self.current_sample[self.label_field_or_dict]


class FiftyOneUnlabeledVideoSampleParser(UnlabeledVideoSampleParser):
    """Parser for :class:`fiftyone.core.sample.Sample` instances that contain
    videos.

    Args:
        compute_metadata (False): whether to compute
            :class:`fiftyone.core.metadata.VideoMetadata` instances on-the-fly
            if :func:`get_video_metadata` is called and no metadata is
            available
    """

    def __init__(self, compute_metadata=False):
        super().__init__()
        self.compute_metadata = compute_metadata

    @property
    def has_video_metadata(self):
        return True

    def get_video_path(self):
        return self.current_sample.filepath

    def get_video_metadata(self):
        metadata = self.current_sample.metadata
        if metadata is None and self.compute_metadata:
            metadata = fom.VideoMetadata.build_for(
                self.current_sample.filepath
            )

        return metadata


class FiftyOneLabeledVideoSampleParser(LabeledVideoSampleParser):
    """Parser for :class:`fiftyone.core.sample.Sample` instances that contain
    labeled videos.

    Args:
        label_field_or_dict (None): the name of a
            :class:`fiftyone.core.labels.Label` field of the sample to parse,
            or a dictionary mapping label field names to output keys to use in
            the returned sample-level labels dictionary
        frame_labels_field_or_dict (None): the name of the frame label field to
            export, or a dictionary mapping field names to output keys
            describing the frame label fields to export
        compute_metadata (False): whether to compute
            :class:`fiftyone.core.metadata.VideoMetadata` instances on-the-fly
            if :func:`get_video_metadata` is called and no metadata is
            available
    """

    def __init__(
        self,
        label_field_or_dict=None,
        frame_labels_field_or_dict=None,
        compute_metadata=False,
    ):
        super().__init__()
        self.label_field_or_dict = label_field_or_dict
        self.frame_labels_dict = self._parse_labels_dict(
            frame_labels_field_or_dict
        )
        self.compute_metadata = compute_metadata

    @property
    def has_video_metadata(self):
        return True

    @property
    def label_cls(self):
        return None

    @property
    def frame_labels_cls(self):
        return None

    def get_video_path(self):
        return self.current_sample.filepath

    def get_video_metadata(self):
        metadata = self.current_sample.metadata
        if metadata is None and self.compute_metadata:
            metadata = fom.VideoMetadata.build_for(
                self.current_sample.filepath
            )

        return metadata

    def get_label(self):
        if self.label_field_or_dict is None:
            return None

        if isinstance(self.label_field_or_dict, dict):
            return {
                v: self.current_sample[k]
                for k, v in self.label_field_or_dict.items()
            }

        return self.current_sample[self.label_field_or_dict]

    def get_frame_labels(self):
        if self.frame_labels_dict is None:
            return None

        frames = self.current_sample.frames
        new_frames = {}
        for frame_number, frame in frames.items():
            new_frames[frame_number] = {
                v: frame[k] for k, v in self.frame_labels_dict.items()
            }

        return new_frames

    @staticmethod
    def _parse_labels_dict(labels_field_or_dict):
        if labels_field_or_dict is None:
            return None

        if not isinstance(labels_field_or_dict, dict):
            return {labels_field_or_dict: labels_field_or_dict}

        return labels_field_or_dict
