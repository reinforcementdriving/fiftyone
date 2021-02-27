"""
Utilities for working with datasets in
`CVAT format <https://github.com/opencv/cvat>`_.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from collections import defaultdict
from copy import copy
from datetime import datetime
import itertools
import logging
import os
import warnings

import jinja2

import eta.core.data as etad
import eta.core.image as etai
import eta.core.utils as etau

import fiftyone as fo
import fiftyone.constants as foc
import fiftyone.core.labels as fol
import fiftyone.core.metadata as fom
import fiftyone.core.utils as fou
import fiftyone.utils.data as foud


logger = logging.getLogger(__name__)


class CVATImageSampleParser(foud.LabeledImageTupleSampleParser):
    """Parser for samples in
    `CVAT image format <https://github.com/opencv/cvat>`_.

    This implementation supports samples that are
    ``(image_or_path, image_tag_dict)`` tuples, where:

        - ``image_or_path`` is either an image that can be converted to numpy
          format via ``np.asarray()`` or the path to an image on disk

        - ``image_tag_dict`` is a JSON dictionary representation of an
          ``<image>`` tag of a CVAT image annotations file which has been
          loaded via :meth:`fiftyone.core.utils.load_xml_as_json_dict`, or
          ``None`` for unlabeled images.

    See :class:`fiftyone.types.dataset_types.CVATImageDataset` for more format
    details.
    """

    def __init__(self):
        super().__init__()
        self._cvat_image_cache = None

    @property
    def has_image_metadata(self):
        return True

    @property
    def label_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def get_image_metadata(self):
        cvat_image = self._cvat_image
        if cvat_image is None:
            return None

        return cvat_image.get_image_metadata()

    def get_label(self):
        """Returns the label for the current sample.

        Args:
            sample: the sample

        Returns:
            a dictionary mapping field names to
            :class:`fiftyone.core.labels.ImageLabel` instances, or ``None`` if
            the sample is unlabeled
        """
        cvat_image = self._cvat_image
        if cvat_image is None:
            return None

        return cvat_image.to_labels()

    def clear_sample(self):
        super().clear_sample()
        self._cvat_image_cache = None

    @property
    def _cvat_image(self):
        if self._cvat_image_cache is None:
            self._cvat_image_cache = self._parse_cvat_image()

        return self._cvat_image_cache

    def _parse_cvat_image(self):
        d = self.current_sample[1]
        return CVATImage.from_image_dict(d) if d is not None else None


class CVATVideoSampleParser(foud.LabeledVideoSampleParser):
    """Parser for samples in
    `CVAT video format <https://github.com/opencv/cvat>`_.

    This implementation supports samples that are
    ``(video_path, image_tag_dict)`` tuples, where:

        - ``video_path`` is the path to a video on disk

        - ``anno_path`` is the path to a CVAT video labels XML file on disk,
          or ``None`` for unlabeled videos.

    See :class:`fiftyone.types.dataset_types.CVATVideoDataset` for more format
    details.
    """

    @property
    def has_video_metadata(self):
        return False

    @property
    def label_cls(self):
        return None

    @property
    def frame_labels_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def get_video_path(self):
        return self.current_sample[0]

    def get_label(self):
        return None

    def get_frame_labels(self):
        labels_path = self.current_sample[1]

        if not labels_path:
            return None

        _, _, cvat_tracks = load_cvat_video_annotations(labels_path)
        return _cvat_tracks_to_frames_dict(cvat_tracks)


class CVATImageDatasetImporter(foud.LabeledImageDatasetImporter):
    """Importer for CVAT image datasets stored on disk.

    See :class:`fiftyone.types.dataset_types.CVATImageDataset` for format
    details.

    Args:
        dataset_dir: the dataset directory
        skip_unlabeled (False): whether to skip unlabeled images when importing
        shuffle (False): whether to randomly shuffle the order in which the
            samples are imported
        seed (None): a random seed to use when shuffling
        max_samples (None): a maximum number of samples to import. By default,
            all samples are imported
    """

    def __init__(
        self,
        dataset_dir,
        skip_unlabeled=False,
        shuffle=False,
        seed=None,
        max_samples=None,
    ):
        super().__init__(
            dataset_dir,
            skip_unlabeled=skip_unlabeled,
            shuffle=shuffle,
            seed=seed,
            max_samples=max_samples,
        )
        self._data_dir = None
        self._labels_path = None
        self._info = None
        self._images_map = None
        self._filenames = None
        self._iter_filenames = None
        self._num_samples = None

    def __iter__(self):
        self._iter_filenames = iter(self._filenames)
        return self

    def __len__(self):
        return self._num_samples

    def __next__(self):
        filename = next(self._iter_filenames)

        image_path = os.path.join(self._data_dir, filename)

        cvat_image = self._images_map.get(filename, None)
        if cvat_image is not None:
            # Labeled image
            image_metadata = cvat_image.get_image_metadata()
            labels = cvat_image.to_labels()
        else:
            # Unlabeled image
            image_metadata = fom.ImageMetadata.build_for(image_path)
            labels = None

        return image_path, image_metadata, labels

    @property
    def has_dataset_info(self):
        return True

    @property
    def has_image_metadata(self):
        return True

    @property
    def label_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def setup(self):
        self._data_dir = os.path.join(self.dataset_dir, "data")
        self._labels_path = os.path.join(self.dataset_dir, "labels.xml")

        if os.path.isfile(self._labels_path):
            info, _, cvat_images = load_cvat_image_annotations(
                self._labels_path
            )
        else:
            info = {}
            cvat_images = []

        self._info = info

        # Index by filename
        self._images_map = {i.name: i for i in cvat_images}

        filenames = etau.list_files(self._data_dir, abs_paths=False)

        if self.skip_unlabeled:
            filenames = [f for f in filenames if f in self._images_map]

        self._filenames = self._preprocess_list(filenames)
        self._num_samples = len(self._filenames)

    def get_dataset_info(self):
        return self._info


class CVATVideoDatasetImporter(foud.LabeledVideoDatasetImporter):
    """Importer for CVAT video datasets stored on disk.

    See :class:`fiftyone.types.dataset_types.CVATVideoDataset` for format
    details.

    Args:
        dataset_dir: the dataset directory
        skip_unlabeled (False): whether to skip unlabeled videos when importing
        shuffle (False): whether to randomly shuffle the order in which the
            samples are imported
        seed (None): a random seed to use when shuffling
        max_samples (None): a maximum number of samples to import. By default,
            all samples are imported
    """

    def __init__(
        self,
        dataset_dir,
        skip_unlabeled=False,
        shuffle=False,
        seed=None,
        max_samples=None,
    ):
        super().__init__(
            dataset_dir,
            skip_unlabeled=skip_unlabeled,
            shuffle=shuffle,
            seed=seed,
            max_samples=max_samples,
        )
        self._info = None
        self._cvat_task_labels = None
        self._uuids_to_video_paths = None
        self._uuids_to_labels_paths = None
        self._uuids = None
        self._iter_uuids = None
        self._num_samples = None

    def __iter__(self):
        self._iter_uuids = iter(self._uuids)
        return self

    def __len__(self):
        return self._num_samples

    def __next__(self):
        uuid = next(self._iter_uuids)

        video_path = self._uuids_to_video_paths[uuid]

        labels_path = self._uuids_to_labels_paths.get(uuid, None)
        if labels_path:
            # Labeled video
            info, cvat_task_labels, cvat_tracks = load_cvat_video_annotations(
                labels_path
            )

            if self._info is None:
                self._info = info

            self._cvat_task_labels.merge_task_labels(cvat_task_labels)
            self._info["task_labels"] = self._cvat_task_labels.labels

            frames = _cvat_tracks_to_frames_dict(cvat_tracks)
        else:
            # Unlabeled video
            frames = None

        return video_path, None, None, frames

    @property
    def has_dataset_info(self):
        return True

    @property
    def has_video_metadata(self):
        return False  # has (width, height) but not other important info

    @property
    def label_cls(self):
        return None

    @property
    def frame_labels_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def setup(self):
        to_uuid = lambda p: os.path.splitext(os.path.basename(p))[0]

        data_dir = os.path.join(self.dataset_dir, "data")
        if os.path.isdir(data_dir):
            self._uuids_to_video_paths = {
                to_uuid(p): p
                for p in etau.list_files(data_dir, abs_paths=True)
            }
        else:
            self._uuids_to_video_paths = {}

        labels_dir = os.path.join(self.dataset_dir, "labels")
        if os.path.isdir(labels_dir):
            self._uuids_to_labels_paths = {
                to_uuid(p): p
                for p in etau.list_files(labels_dir, abs_paths=True)
            }
        else:
            self._uuids_to_labels_paths = {}

        if self.skip_unlabeled:
            uuids = sorted(self._uuids_to_labels_paths.keys())
        else:
            uuids = sorted(self._uuids_to_video_paths.keys())

        self._info = None
        self._uuids = self._preprocess_list(uuids)
        self._num_samples = len(self._uuids)
        self._cvat_task_labels = CVATTaskLabels()

    def get_dataset_info(self):
        return self._info


class CVATImageDatasetExporter(foud.LabeledImageDatasetExporter):
    """Exporter that writes CVAT image datasets to disk.

    See :class:`fiftyone.types.dataset_types.CVATImageDataset` for format
    details.

    Args:
        export_dir: the directory to write the export
        image_format (None): the image format to use when writing in-memory
            images to disk. By default, ``fiftyone.config.default_image_ext``
            is used
    """

    def __init__(self, export_dir, image_format=None):
        if image_format is None:
            image_format = fo.config.default_image_ext

        super().__init__(export_dir)
        self.image_format = image_format
        self._name = None
        self._task_labels = None
        self._data_dir = None
        self._labels_path = None
        self._cvat_images = None
        self._filename_maker = None

    @property
    def requires_image_metadata(self):
        return True

    @property
    def label_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def setup(self):
        self._data_dir = os.path.join(self.export_dir, "data")
        self._labels_path = os.path.join(self.export_dir, "labels.xml")
        self._cvat_images = []
        self._filename_maker = fou.UniqueFilenameMaker(
            output_dir=self._data_dir, default_ext=self.image_format
        )

    def log_collection(self, sample_collection):
        self._name = sample_collection.name
        self._task_labels = sample_collection.info.get("task_labels", None)

    def export_sample(self, image_or_path, labels, metadata=None):
        out_image_path = self._export_image_or_path(
            image_or_path, self._filename_maker
        )

        if labels is None:
            return  # unlabeled

        if not isinstance(labels, dict):
            labels = {"labels": labels}

        if all(v is None for v in labels.values()):
            return  # unlabeled

        if metadata is None:
            metadata = fom.ImageMetadata.build_for(out_image_path)

        cvat_image = CVATImage.from_labels(labels, metadata)

        cvat_image.id = len(self._cvat_images)
        cvat_image.name = os.path.basename(out_image_path)

        self._cvat_images.append(cvat_image)

    def close(self, *args):
        # Get task labels
        if self._task_labels is None:
            # Compute task labels from active label schema
            cvat_task_labels = CVATTaskLabels.from_cvat_images(
                self._cvat_images
            )
        else:
            # Use task labels from logged collection info
            cvat_task_labels = CVATTaskLabels(labels=self._task_labels)

        # Write annotations
        writer = CVATImageAnnotationWriter()
        writer.write(
            cvat_task_labels,
            self._cvat_images,
            self._labels_path,
            id=0,
            name=self._name,
        )


class CVATVideoDatasetExporter(foud.LabeledVideoDatasetExporter):
    """Exporter that writes CVAT video datasets to disk.

    See :class:`fiftyone.types.dataset_types.CVATVideoDataset` for format
    details.

    Args:
        export_dir: the directory to write the export
    """

    def __init__(self, export_dir):
        super().__init__(export_dir)
        self._task_labels = None
        self._data_dir = None
        self._labels_dir = None
        self._filename_maker = None
        self._writer = None
        self._num_samples = 0

    @property
    def requires_video_metadata(self):
        return True

    @property
    def label_cls(self):
        return None

    @property
    def frame_labels_cls(self):
        return {
            "detections": fol.Detections,
            "polylines": fol.Polylines,
            "keypoints": fol.Keypoints,
        }

    def setup(self):
        self._data_dir = os.path.join(self.export_dir, "data")
        self._labels_dir = os.path.join(self.export_dir, "labels")
        self._filename_maker = fou.UniqueFilenameMaker(
            output_dir=self._data_dir
        )
        self._writer = CVATVideoAnnotationWriter()

        etau.ensure_dir(self._data_dir)
        etau.ensure_dir(self._labels_dir)

    def log_collection(self, sample_collection):
        self._task_labels = sample_collection.info.get("task_labels", None)

    def export_sample(self, video_path, _, frames, metadata=None):
        out_video_path = self._export_video(video_path, self._filename_maker)

        if frames is None:
            return  # unlabeled

        if metadata is None:
            metadata = fom.VideoMetadata.build_for(out_video_path)

        name_with_ext = os.path.basename(out_video_path)
        name = os.path.splitext(name_with_ext)[0]
        out_anno_path = os.path.join(self._labels_dir, name + ".xml")

        # Generate object tracks
        frame_size = (metadata.frame_width, metadata.frame_height)
        cvat_tracks = _frames_to_cvat_tracks(frames, frame_size)

        if cvat_tracks is None:
            return  # unlabeled

        # Get task labels
        if self._task_labels is None:
            # Compute task labels from active label schema
            cvat_task_labels = CVATTaskLabels.from_cvat_tracks(cvat_tracks)
        else:
            # Use task labels from logged collection info
            cvat_task_labels = CVATTaskLabels(labels=self._task_labels)

        # Write annotations
        self._num_samples += 1
        self._writer.write(
            cvat_task_labels,
            cvat_tracks,
            metadata,
            out_anno_path,
            id=self._num_samples - 1,
            name=name_with_ext,
        )


class CVATTaskLabels(object):
    """Description of the labels in a CVAT image annotation task.

    Args:
        labels (None): a list of label dicts in the following format::

            [
                {
                    "name": "car",
                    "attributes": [
                        {
                            "name": "type"
                            "categories": ["coupe", "sedan", "truck"]
                        },
                        ...
                    }
                },
                ...
            ]
    """

    def __init__(self, labels=None):
        self.labels = labels or []

    def merge_task_labels(self, task_labels):
        """Merges the given :class:`CVATTaskLabels` into this instance.

        Args:
            task_labels: a :class:`CVATTaskLabels`
        """
        schema = self.to_schema()
        schema.merge_schema(task_labels.to_schema())
        new_task_labels = CVATTaskLabels.from_schema(schema)
        self.labels = new_task_labels.labels

    def to_schema(self):
        """Returns an ``eta.core.image.ImageLabelsSchema`` representation of
        the task labels.

        Note that CVAT's task labels schema does not distinguish between boxes,
        polylines, and keypoints, so the returned schema stores all annotations
        under the ``"objects"`` field.

        Returns:
            an ``eta.core.image.ImageLabelsSchema``
        """
        schema = etai.ImageLabelsSchema()

        for label in self.labels:
            _label = label["name"]
            schema.add_object_label(_label)
            for attribute in label.get("attributes", []):
                _name = attribute["name"]
                _categories = attribute["categories"]
                for _value in _categories:
                    _attr = etad.CategoricalAttribute(_name, _value)
                    schema.add_object_attribute(_label, _attr)

        return schema

    @classmethod
    def from_cvat_images(cls, cvat_images):
        """Creates a :class:`CVATTaskLabels` instance that describes the active
        schema of the given annotations.

        Args:
            cvat_images: a list of :class:`CVATImage` instances

        Returns:
            a :class:`CVATTaskLabels`
        """
        schema = etai.ImageLabelsSchema()
        for cvat_image in cvat_images:
            for anno in cvat_image.iter_annos():
                _label = anno.label
                schema.add_object_label(_label)

                if anno.occluded is not None:
                    schema.add_object_attribute("occluded", anno.occluded)

                for attr in anno.attributes:
                    _attr = attr.to_eta_attribute()
                    schema.add_object_attribute(_label, _attr)

        return cls.from_schema(schema)

    @classmethod
    def from_cvat_tracks(cls, cvat_tracks):
        """Creates a :class:`CVATTaskLabels` instance that describes the active
        schema of the given annotations.

        Args:
            cvat_tracks: a list of :class:`CVATTrack` instances

        Returns:
            a :class:`CVATTaskLabels`
        """
        schema = etai.ImageLabelsSchema()
        for cvat_track in cvat_tracks:
            for anno in cvat_track.iter_annos():
                _label = anno.label
                schema.add_object_label(_label)

                if anno.outside is not None:
                    schema.add_object_attribute("outside", anno.outside)

                if anno.occluded is not None:
                    schema.add_object_attribute("occluded", anno.occluded)

                if anno.keyframe is not None:
                    schema.add_object_attribute("keyframe", anno.keyframe)

                for attr in anno.attributes:
                    _attr = attr.to_eta_attribute()
                    schema.add_object_attribute(_label, _attr)

        return cls.from_schema(schema)

    @classmethod
    def from_labels_dict(cls, d):
        """Creates a :class:`CVATTaskLabels` instance from the ``<labels>``
        tag of a CVAT image annotation XML file.

        Args:
            d: a dict representation of a ``<labels>`` tag

        Returns:
            a :class:`CVATTaskLabels`
        """
        labels = _ensure_list(d.get("label", []))
        _labels = []
        for label in labels:
            _tmp = label.get("attributes", None) or {}
            attributes = _ensure_list(_tmp.get("attribute", []))
            _attributes = []
            for attribute in attributes:
                _attributes.append(
                    {
                        "name": attribute["name"],
                        "categories": attribute["values"].split("\n"),
                    }
                )

            _labels.append({"name": label["name"], "attributes": _attributes})

        return cls(labels=_labels)

    @classmethod
    def from_schema(cls, schema):
        """Creates a :class:`CVATTaskLabels` instance from an
        ``eta.core.image.ImageLabelsSchema``.

        Args:
            schema: an ``eta.core.image.ImageLabelsSchema``

        Returns:
            a :class:`CVATTaskLabels`
        """
        labels = []
        obj_schemas = schema.objects
        for label in sorted(obj_schemas.schema):
            obj_schema = obj_schemas.schema[label]
            obj_attr_schemas = obj_schema.attrs
            attributes = []
            for name in sorted(obj_attr_schemas.schema):
                attr_schema = obj_attr_schemas.schema[name]
                if isinstance(attr_schema, etad.CategoricalAttributeSchema):
                    attributes.append(
                        {
                            "name": name,
                            "categories": sorted(attr_schema.categories),
                        }
                    )

            labels.append({"name": label, "attributes": attributes})

        return cls(labels=labels)


class CVATImage(object):
    """An annotated image in CVAT image format.

    Args:
        id: the ID of the image
        name: the filename of the image
        width: the width of the image, in pixels
        height: the height of the image, in pixels
        boxes (None): a list of :class:`CVATImageBox` instances
        polygons (None): a list of :class:`CVATImagePolygon` instances
        polylines (None): a list of :class:`CVATImagePolyline` instances
        points (None): a list of :class:`CVATImagePoints` instances
    """

    def __init__(
        self,
        id,
        name,
        width,
        height,
        boxes=None,
        polygons=None,
        polylines=None,
        points=None,
    ):
        self.id = id
        self.name = name
        self.width = width
        self.height = height
        self.boxes = boxes or []
        self.polygons = polygons or []
        self.polylines = polylines or []
        self.points = points or []

    @property
    def has_boxes(self):
        """Whether this image has 2D boxes."""
        return bool(self.boxes)

    @property
    def has_polylines(self):
        """Whether this image has polygons or polylines."""
        return bool(self.polygons) or bool(self.polylines)

    @property
    def has_points(self):
        """Whether this image has keypoints."""
        return bool(self.points)

    def iter_annos(self):
        """Returns an iterator over the annotations in the image.

        Returns:
            an iterator that emits :class:`CVATImageAnno` instances
        """
        return itertools.chain(
            self.boxes, self.polygons, self.polylines, self.points
        )

    def get_image_metadata(self):
        """Returns a :class:`fiftyone.core.metadata.ImageMetadata` instance for
        the annotations.

        Returns:
            a :class:`fiftyone.core.metadata.ImageMetadata`
        """
        return fom.ImageMetadata(width=self.width, height=self.height)

    def to_labels(self):
        """Returns :class:`fiftyone.core.labels.ImageLabel` representations of
        the annotations.

        Returns:
            a dictionary mapping field keys to
            :class:`fiftyone.core.labels.ImageLabel` containers
        """
        frame_size = (self.width, self.height)

        labels = {}

        if self.boxes:
            detections = [b.to_detection(frame_size) for b in self.boxes]
            labels["detections"] = fol.Detections(detections=detections)

        if self.polygons or self.polylines:
            polygons = [p.to_polyline(frame_size) for p in self.polygons]
            polylines = [p.to_polyline(frame_size) for p in self.polylines]
            labels["polylines"] = fol.Polylines(polylines=polygons + polylines)

        if self.points:
            keypoints = [k.to_keypoint(frame_size) for k in self.points]
            labels["keypoints"] = fol.Keypoints(keypoints=keypoints)

        return labels

    @classmethod
    def from_labels(cls, labels, metadata):
        """Creates a :class:`CVATImage` from a dictionary of labels.

        Args:
            labels: a dictionary mapping keys to
                :class:`fiftyone.core.labels.ImageLabel` containers
            metadata: a :class:`fiftyone.core.metadata.ImageMetadata` for the
                image

        Returns:
            a :class:`CVATImage`
        """
        width = metadata.width
        height = metadata.height

        _detections = []
        _polygons = []
        _polylines = []
        _keypoints = []
        for _labels in labels.values():
            if isinstance(_labels, fol.Detection):
                _detections.append(_labels)
            elif isinstance(_labels, fol.Detections):
                _detections.extend(_labels.detections)
            elif isinstance(_labels, fol.Polyline):
                if _labels.closed:
                    _polygons.append(_labels)
                else:
                    _polylines.append(_labels)
            elif isinstance(_labels, fol.Polylines):
                for poly in _labels.polylines:
                    if poly.closed:
                        _polygons.append(poly)
                    else:
                        _polylines.append(poly)
            elif isinstance(_labels, fol.Keypoint):
                _keypoints.append(_labels)
            elif isinstance(_labels, fol.Keypoints):
                _keypoints.extend(_labels.keypoints)
            elif _labels is not None:
                msg = (
                    "Ignoring unsupported label type '%s'" % _labels.__class__
                )
                warnings.warn(msg)

        boxes = [CVATImageBox.from_detection(d, metadata) for d in _detections]

        polygons = []
        for p in _polygons:
            polygons.extend(CVATImagePolygon.from_polyline(p, metadata))

        polylines = []
        for p in _polylines:
            polylines.extend(CVATImagePolyline.from_polyline(p, metadata))

        points = [
            CVATImagePoints.from_keypoint(k, metadata) for k in _keypoints
        ]

        return cls(
            None,
            None,
            width,
            height,
            boxes=boxes,
            polygons=polygons,
            polylines=polylines,
            points=points,
        )

    @classmethod
    def from_image_dict(cls, d):
        """Creates a :class:`CVATImage` from an ``<image>`` tag of a CVAT image
        annotations XML file.

        Args:
            d: a dict representation of an ``<image>`` tag

        Returns:
            a :class:`CVATImage`
        """
        id = d["@id"]
        name = d["@name"]
        width = int(d["@width"])
        height = int(d["@height"])

        boxes = []
        for bd in _ensure_list(d.get("box", [])):
            boxes.append(CVATImageBox.from_box_dict(bd))

        polygons = []
        for pd in _ensure_list(d.get("polygon", [])):
            polygons.append(CVATImagePolygon.from_polygon_dict(pd))

        polylines = []
        for pd in _ensure_list(d.get("polyline", [])):
            polylines.append(CVATImagePolyline.from_polyline_dict(pd))

        points = []
        for pd in _ensure_list(d.get("points", [])):
            points.append(CVATImagePoints.from_points_dict(pd))

        return cls(
            id,
            name,
            width,
            height,
            boxes=boxes,
            polygons=polygons,
            polylines=polylines,
            points=points,
        )


class HasCVATPoints(object):
    """Mixin for CVAT annotations that store a list of ``(x, y)`` pixel
    coordinates.

    Attributes:
        points: a list of ``(x, y)`` pixel coordinates defining points
    """

    def __init__(self, points):
        self.points = points

    @property
    def points_str(self):
        return self._to_cvat_points_str(self.points)

    @staticmethod
    def _to_rel_points(points, frame_size):
        width, height = frame_size
        rel_points = [(x / width, y / height) for x, y in points]
        return rel_points

    @staticmethod
    def _to_abs_points(points, frame_size):
        width, height = frame_size
        abs_points = []
        for x, y in points:
            abs_points.append((int(round(x * width)), int(round(y * height))))

        return abs_points

    @staticmethod
    def _to_cvat_points_str(points):
        return ";".join("%g,%g" % (x, y) for x, y in points)

    @staticmethod
    def _parse_cvat_points_str(points_str):
        points = []
        for xy_str in points_str.split(";"):
            x, y = xy_str.split(",")
            points.append((int(round(float(x))), int(round(float(y)))))

        return points


class CVATImageAnno(object):
    """Mixin for annotations in CVAT image format.

    Args:
        occluded (None): whether the object is occluded
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(self, occluded=None, attributes=None):
        self.occluded = occluded
        self.attributes = attributes or []

    def _to_attributes(self):
        attributes = {a.name: a.to_attribute() for a in self.attributes}

        if self.occluded is not None:
            attributes["occluded"] = fol.BooleanAttribute(value=self.occluded)

        return attributes

    @staticmethod
    def _parse_attributes(label):
        occluded = None

        if label.attributes:
            supported_attrs = (
                fol.BooleanAttribute,
                fol.CategoricalAttribute,
                fol.NumericAttribute,
            )

            attributes = []
            for name, attr in label.attributes.items():
                if name == "occluded":
                    occluded = attr.value
                elif isinstance(attr, supported_attrs):
                    attributes.append(CVATAttribute(name, attr.value))
        else:
            attributes = None

        return occluded, attributes

    @staticmethod
    def _parse_anno_dict(d):
        occluded = d.get("@occluded", None)
        if occluded is not None:
            occluded = bool(int(occluded))

        attributes = []
        for attr in _ensure_list(d.get("attribute", [])):
            name = attr["@name"].lstrip("@")
            value = attr["#text"]
            try:
                value = float(value)
            except:
                pass

            attributes.append(CVATAttribute(name, value))

        return occluded, attributes


class CVATImageBox(CVATImageAnno):
    """An object bounding box in CVAT image format.

    Args:
        label: the object label string
        xtl: the top-left x-coordinate of the box, in pixels
        ytl: the top-left y-coordinate of the box, in pixels
        xbr: the bottom-right x-coordinate of the box, in pixels
        ybr: the bottom-right y-coordinate of the box, in pixels
        occluded (None): whether the object is occluded
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self, label, xtl, ytl, xbr, ybr, occluded=None, attributes=None
    ):
        self.label = label
        self.xtl = xtl
        self.ytl = ytl
        self.xbr = xbr
        self.ybr = ybr
        CVATImageAnno.__init__(self, occluded=occluded, attributes=attributes)

    def to_detection(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Detection` representation of
        the box.

        Args:
            frame_size: the ``(width, height)`` of the image

        Returns:
            a :class:`fiftyone.core.labels.Detection`
        """
        label = self.label

        width, height = frame_size
        bounding_box = [
            self.xtl / width,
            self.ytl / height,
            (self.xbr - self.xtl) / width,
            (self.ybr - self.ytl) / height,
        ]

        attributes = self._to_attributes()

        return fol.Detection(
            label=label, bounding_box=bounding_box, attributes=attributes,
        )

    @classmethod
    def from_detection(cls, detection, metadata):
        """Creates a :class:`CVATImageBox` from a
        :class:`fiftyone.core.labels.Detection`.

        Args:
            detection: a :class:`fiftyone.core.labels.Detection`
            metadata: a :class:`fiftyone.core.metadata.ImageMetadata` for the
                image

        Returns:
            a :class:`CVATImageBox`
        """
        label = detection.label

        width = metadata.width
        height = metadata.height
        x, y, w, h = detection.bounding_box
        xtl = int(round(x * width))
        ytl = int(round(y * height))
        xbr = int(round((x + w) * width))
        ybr = int(round((y + h) * height))

        occluded, attributes = cls._parse_attributes(detection)

        return cls(
            label, xtl, ytl, xbr, ybr, occluded=occluded, attributes=attributes
        )

    @classmethod
    def from_box_dict(cls, d):
        """Creates a :class:`CVATImageBox` from a ``<box>`` tag of a CVAT image
        annotation XML file.

        Args:
            d: a dict representation of a ``<box>`` tag

        Returns:
            a :class:`CVATImageBox`
        """
        label = d["@label"]

        xtl = int(round(float(d["@xtl"])))
        ytl = int(round(float(d["@ytl"])))
        xbr = int(round(float(d["@xbr"])))
        ybr = int(round(float(d["@ybr"])))

        occluded, attributes = cls._parse_anno_dict(d)

        return cls(
            label, xtl, ytl, xbr, ybr, occluded=occluded, attributes=attributes
        )


class CVATImagePolygon(CVATImageAnno, HasCVATPoints):
    """A polygon in CVAT image format.

    Args:
        label: the polygon label string
        points: a list of ``(x, y)`` pixel coordinates defining the vertices of
            the polygon
        occluded (None): whether the polygon is occluded
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(self, label, points, occluded=None, attributes=None):
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATImageAnno.__init__(self, occluded=occluded, attributes=attributes)

    def to_polyline(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Polyline` representation of
        the polygon.

        Args:
            frame_size: the ``(width, height)`` of the image

        Returns:
            a :class:`fiftyone.core.labels.Polyline`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Polyline(
            label=label,
            points=[points],
            closed=True,
            filled=True,
            attributes=attributes,
        )

    @classmethod
    def from_polyline(cls, polyline, metadata):
        """Creates a :class:`CVATImagePolygon` from a
        :class:`fiftyone.core.labels.Polyline`.

        If the :class:`fiftyone.core.labels.Polyline` is composed of multiple
        shapes, one :class:`CVATImagePolygon` per shape will be generated.

        Args:
            polyline: a :class:`fiftyone.core.labels.Polyline`
            metadata: a :class:`fiftyone.core.metadata.ImageMetadata` for the
                image

        Returns:
            a list of :class:`CVATImagePolygon` instances
        """
        label = polyline.label

        if len(polyline.points) > 1:
            msg = (
                "Found polyline with more than one shape; generating separate "
                "annotations for each shape"
            )
            warnings.warn(msg)

        frame_size = (metadata.width, metadata.height)
        occluded, attributes = cls._parse_attributes(polyline)

        polylines = []
        for points in polyline.points:
            abs_points = cls._to_abs_points(points, frame_size)
            polylines.append(
                cls(
                    label, abs_points, occluded=occluded, attributes=attributes
                )
            )

        return polylines

    @classmethod
    def from_polygon_dict(cls, d):
        """Creates a :class:`CVATImagePolygon` from a ``<polygon>`` tag of a
        CVAT image annotation XML file.

        Args:
            d: a dict representation of a ``<polygon>`` tag

        Returns:
            a :class:`CVATImagePolygon`
        """
        label = d["@label"]
        points = cls._parse_cvat_points_str(d["@points"])
        occluded, attributes = cls._parse_anno_dict(d)

        return cls(label, points, occluded=occluded, attributes=attributes)


class CVATImagePolyline(CVATImageAnno, HasCVATPoints):
    """A polyline in CVAT image format.

    Args:
        label: the polyline label string
        points: a list of ``(x, y)`` pixel coordinates defining the vertices of
            the polyline
        occluded (None): whether the polyline is occluded
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(self, label, points, occluded=None, attributes=None):
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATImageAnno.__init__(self, occluded=occluded, attributes=attributes)

    def to_polyline(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Polyline` representation of
        the polyline.

        Args:
            frame_size: the ``(width, height)`` of the image

        Returns:
            a :class:`fiftyone.core.labels.Polyline`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Polyline(
            label=label,
            points=[points],
            closed=False,
            filled=False,
            attributes=attributes,
        )

    @classmethod
    def from_polyline(cls, polyline, metadata):
        """Creates a :class:`CVATImagePolyline` from a
        :class:`fiftyone.core.labels.Polyline`.

        If the :class:`fiftyone.core.labels.Polyline` is composed of multiple
        shapes, one :class:`CVATImagePolyline` per shape will be generated.

        Args:
            polyline: a :class:`fiftyone.core.labels.Polyline`
            metadata: a :class:`fiftyone.core.metadata.ImageMetadata` for the
                image

        Returns:
            a list of :class:`CVATImagePolyline` instances
        """
        label = polyline.label

        if len(polyline.points) > 1:
            msg = (
                "Found polyline with more than one shape; generating separate "
                "annotations for each shape"
            )
            warnings.warn(msg)

        frame_size = (metadata.width, metadata.height)
        occluded, attributes = cls._parse_attributes(polyline)

        polylines = []
        for points in polyline.points:
            abs_points = cls._to_abs_points(points, frame_size)
            if abs_points and polyline.closed:
                abs_points.append(copy(abs_points[0]))

            polylines.append(
                cls(
                    label, abs_points, occluded=occluded, attributes=attributes
                )
            )

        return polylines

    @classmethod
    def from_polyline_dict(cls, d):
        """Creates a :class:`CVATImagePolyline` from a ``<polyline>`` tag of a
        CVAT image annotation XML file.

        Args:
            d: a dict representation of a ``<polyline>`` tag

        Returns:
            a :class:`CVATImagePolyline`
        """
        label = d["@label"]
        points = cls._parse_cvat_points_str(d["@points"])
        occluded, attributes = cls._parse_anno_dict(d)

        return cls(label, points, occluded=occluded, attributes=attributes)


class CVATImagePoints(CVATImageAnno, HasCVATPoints):
    """A set of keypoints in CVAT image format.

    Args:
        label: the keypoints label string
        points: a list of ``(x, y)`` pixel coordinates defining the vertices of
            the keypoints
        occluded (None): whether the keypoints are occluded
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(self, label, points, occluded=None, attributes=None):
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATImageAnno.__init__(self, occluded=occluded, attributes=attributes)

    def to_keypoint(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Keypoint` representation of
        the points.

        Args:
            frame_size: the ``(width, height)`` of the image

        Returns:
            a :class:`fiftyone.core.labels.Keypoint`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Keypoint(label=label, points=points, attributes=attributes)

    @classmethod
    def from_keypoint(cls, keypoint, metadata):
        """Creates a :class:`CVATImagePoints` from a
        :class:`fiftyone.core.labels.Keypoint`.

        Args:
            keypoint: a :class:`fiftyone.core.labels.Keypoint`
            metadata: a :class:`fiftyone.core.metadata.ImageMetadata` for the
                image

        Returns:
            a :class:`CVATImagePoints`
        """
        label = keypoint.label

        frame_size = (metadata.width, metadata.height)
        points = cls._to_abs_points(keypoint.points, frame_size)

        occluded, attributes = cls._parse_attributes(keypoint)

        return cls(label, points, occluded=occluded, attributes=attributes)

    @classmethod
    def from_points_dict(cls, d):
        """Creates a :class:`CVATImagePoints` from a ``<points>`` tag of a
        CVAT image annotation XML file.

        Args:
            d: a dict representation of a ``<points>`` tag

        Returns:
            a :class:`CVATImagePoints`
        """
        label = d["@label"]
        points = cls._parse_cvat_points_str(d["@points"])
        occluded, attributes = cls._parse_anno_dict(d)
        return cls(label, points, occluded=occluded, attributes=attributes)


class CVATTrack(object):
    """An annotation track in CVAT video format.

    Args:
        id: the ID of the track
        label: the label for the track
        width: the width of the video frames, in pixels
        height: the height of the video frames, in pixels
        boxes (None): a dict mapping frame numbers to :class:`CVATVideoBox`
            instances
        polygons (None): a dict mapping frame numbers to
            :class:`CVATVideoPolygon` instances
        polylines (None): a dict mapping frame numbers to
            :class:`CVATVideoPolyline` instances
        points (None): a dict mapping frame numbers to :class:`CVATVideoPoints`
            instances
    """

    def __init__(
        self,
        id,
        label,
        width,
        height,
        boxes=None,
        polygons=None,
        polylines=None,
        points=None,
    ):
        self.id = id
        self.label = label
        self.width = width
        self.height = height
        self.boxes = boxes or {}
        self.polygons = polygons or {}
        self.polylines = polylines or {}
        self.points = points or {}

    @property
    def has_boxes(self):
        """Whether this track has 2D boxes."""
        return bool(self.boxes)

    @property
    def has_polylines(self):
        """Whether this track has polygons or polylines."""
        return bool(self.polygons) or bool(self.polylines)

    @property
    def has_points(self):
        """Whether this track has keypoints."""
        return bool(self.points)

    def iter_annos(self):
        """Returns an iterator over the annotations in the track.

        Returns:
            an iterator that emits :class:`CVATVideoAnno` instances
        """
        return itertools.chain(
            self.boxes.values(),
            self.polygons.values(),
            self.polylines.values(),
            self.points.values(),
        )

    def to_labels(self):
        """Returns :class:`fiftyone.core.labels.ImageLabel` representations of
        the annotations.

        Returns:
            a dictionary mapping frame numbers to
            :class:`fiftyone.core.labels.ImageLabel` instances
        """
        frame_size = (self.width, self.height)

        labels = {}

        # Only one of these will actually contain labels

        for frame_number, box in self.boxes.items():
            detection = box.to_detection(frame_size)
            detection.index = self.id
            labels[frame_number] = detection

        for frame_number, polygon in self.polygons.items():
            polyline = polygon.to_polyline(frame_size)
            polyline.index = self.id
            labels[frame_number] = polyline

        for frame_number, polyline in self.polylines.items():
            polyline = polyline.to_polyline(frame_size)
            polyline.index = self.id
            labels[frame_number] = polyline

        for frame_number, points in self.points.items():
            keypoint = points.to_keypoint(frame_size)
            keypoint.index = self.id
            labels[frame_number] = keypoint

        return labels

    @classmethod
    def from_labels(cls, id, labels, frame_size):
        """Creates a :class:`CVATTrack` from a dictionary of labels.

        Args:
            id: the ID of the track
            labels: a dictionary mapping frame numbers to
                :class:`fiftyone.core.labels.ImageLabel` instances
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATTrack`
        """
        width, height = frame_size

        boxes = {}
        polygons = {}
        polylines = {}
        points = {}
        label = None
        for frame_number, _label in labels.items():
            label = _label.label

            if isinstance(_label, fol.Detection):
                boxes[frame_number] = CVATVideoBox.from_detection(
                    frame_number, _label, frame_size
                )
            elif isinstance(_label, fol.Polyline):
                if _label.filled:
                    polygons[frame_number] = CVATVideoPolygon.from_polyline(
                        frame_number, _label, frame_size
                    )
                else:
                    polylines[frame_number] = CVATVideoPolyline.from_polyline(
                        frame_number, _label, frame_size
                    )
            elif isinstance(_label, fol.Keypoint):
                points[frame_number] = CVATVideoPoints.from_keypoint(
                    frame_number, _label, frame_size
                )
            elif _label is not None:
                msg = "Ignoring unsupported label type '%s'" % _label.__class__
                warnings.warn(msg)

        return cls(
            id,
            label,
            width,
            height,
            boxes=boxes,
            polygons=polygons,
            polylines=polylines,
            points=points,
        )

    @classmethod
    def from_track_dict(cls, d, frame_size):
        """Creates a :class:`CVATTrack` from a ``<track>`` tag of a CVAT video
        annotation XML file.

        Args:
            d: a dict representation of an ``<track>`` tag
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATTrack`
        """
        id = d["@id"]
        label = d["@label"]

        width, height = frame_size

        boxes = {}
        for bd in _ensure_list(d.get("box", [])):
            box = CVATVideoBox.from_box_dict(label, bd)
            boxes[box.frame] = box

        polygons = {}
        for pd in _ensure_list(d.get("polygon", [])):
            polygon = CVATVideoPolygon.from_polygon_dict(label, pd)
            polygons[polygon.frame] = polygon

        polylines = {}
        for pd in _ensure_list(d.get("polyline", [])):
            polyline = CVATVideoPolyline.from_polyline_dict(label, pd)
            polylines[polyline.frame] = polyline

        points = {}
        for pd in _ensure_list(d.get("points", [])):
            point = CVATVideoPoints.from_points_dict(label, pd)
            points[point.frame] = point

        return cls(
            id,
            label,
            width,
            height,
            boxes=boxes,
            polygons=polygons,
            polylines=polylines,
            points=points,
        )


class CVATVideoAnno(object):
    """Mixin for annotations in CVAT video format.

    Args:
        outside (None): whether the object is truncated by the frame edge
        occluded (None): whether the object is occluded
        keyframe (None): whether the frame is a key frame
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self, outside=None, occluded=None, keyframe=None, attributes=None
    ):
        self.outside = outside
        self.occluded = occluded
        self.keyframe = keyframe
        self.attributes = attributes or []

    def _to_attributes(self):
        attributes = {a.name: a.to_attribute() for a in self.attributes}

        if self.outside is not None:
            attributes["outside"] = fol.BooleanAttribute(value=self.outside)

        if self.occluded is not None:
            attributes["occluded"] = fol.BooleanAttribute(value=self.occluded)

        if self.keyframe is not None:
            attributes["keyframe"] = fol.BooleanAttribute(value=self.keyframe)

        return attributes

    @staticmethod
    def _parse_attributes(label):
        outside = None
        occluded = None
        keyframe = None

        if label.attributes:
            supported_attrs = (
                fol.BooleanAttribute,
                fol.CategoricalAttribute,
                fol.NumericAttribute,
            )

            attributes = []
            for name, attr in label.attributes.items():
                if name == "outside":
                    outside = attr.value
                elif name == "occluded":
                    occluded = attr.value
                elif name == "keyframe":
                    keyframe = attr.value
                elif isinstance(attr, supported_attrs):
                    attributes.append(CVATAttribute(name, attr.value))
        else:
            attributes = None

        return outside, occluded, keyframe, attributes

    @staticmethod
    def _parse_anno_dict(d):
        outside = d.get("@outside", None)
        if outside is not None:
            outside = bool(int(outside))

        occluded = d.get("@occluded", None)
        if occluded is not None:
            occluded = bool(int(occluded))

        keyframe = d.get("@keyframe", None)
        if keyframe is not None:
            keyframe = bool(int(keyframe))

        attributes = []
        for attr in _ensure_list(d.get("attribute", [])):
            name = attr["@name"].lstrip("@")
            value = attr["#text"]
            try:
                value = float(value)
            except:
                pass

            attributes.append(CVATAttribute(name, value))

        return outside, occluded, keyframe, attributes


class CVATVideoBox(CVATVideoAnno):
    """An object bounding box in CVAT video format.

    Args:
        frame: the frame number
        label: the object label string
        xtl: the top-left x-coordinate of the box, in pixels
        ytl: the top-left y-coordinate of the box, in pixels
        xbr: the bottom-right x-coordinate of the box, in pixels
        ybr: the bottom-right y-coordinate of the box, in pixels
        outside (None): whether the object is truncated by the frame edge
        occluded (None): whether the object is occluded
        keyframe (None): whether the frame is a key frame
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self,
        frame,
        label,
        xtl,
        ytl,
        xbr,
        ybr,
        outside=None,
        occluded=None,
        keyframe=None,
        attributes=None,
    ):
        self.frame = frame
        self.label = label
        self.xtl = xtl
        self.ytl = ytl
        self.xbr = xbr
        self.ybr = ybr
        CVATVideoAnno.__init__(
            self,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    def to_detection(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Detection` representation of
        the box.

        Args:
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`fiftyone.core.labels.Detection`
        """
        label = self.label

        width, height = frame_size
        bounding_box = [
            self.xtl / width,
            self.ytl / height,
            (self.xbr - self.xtl) / width,
            (self.ybr - self.ytl) / height,
        ]

        attributes = self._to_attributes()

        return fol.Detection(
            label=label, bounding_box=bounding_box, attributes=attributes,
        )

    @classmethod
    def from_detection(cls, frame_number, detection, frame_size):
        """Creates a :class:`CVATVideoBox` from a
        :class:`fiftyone.core.labels.Detection`.

        Args:
            frame_number: the frame number
            detection: a :class:`fiftyone.core.labels.Detection`
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATVideoBox`
        """
        label = detection.label

        width, height = frame_size
        x, y, w, h = detection.bounding_box
        xtl = int(round(x * width))
        ytl = int(round(y * height))
        xbr = int(round((x + w) * width))
        ybr = int(round((y + h) * height))

        outside, occluded, keyframe, attributes = cls._parse_attributes(
            detection
        )

        return cls(
            frame_number,
            label,
            xtl,
            ytl,
            xbr,
            ybr,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    @classmethod
    def from_box_dict(cls, label, d):
        """Creates a :class:`CVATVideoBox` from a ``<box>`` tag of a CVAT video
        annotation XML file.

        Args:
            label: the object label
            d: a dict representation of a ``<box>`` tag

        Returns:
            a :class:`CVATVideoBox`
        """
        frame = int(d["@frame"])

        xtl = int(round(float(d["@xtl"])))
        ytl = int(round(float(d["@ytl"])))
        xbr = int(round(float(d["@xbr"])))
        ybr = int(round(float(d["@ybr"])))

        outside, occluded, keyframe, attributes = cls._parse_anno_dict(d)

        return cls(
            frame,
            label,
            xtl,
            ytl,
            xbr,
            ybr,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )


class CVATVideoPolygon(CVATVideoAnno, HasCVATPoints):
    """A polygon in CVAT video format.

    Args:
        frame: the frame number
        label: the polygon label string
        points: a list of ``(x, y)`` pixel coordinates defining the vertices of
            the polygon
        outside (None): whether the polygon is truncated by the frame edge
        occluded (None): whether the polygon is occluded
        keyframe (None): whether the frame is a key frame
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self,
        frame,
        label,
        points,
        outside=None,
        occluded=None,
        keyframe=None,
        attributes=None,
    ):
        self.frame = frame
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATVideoAnno.__init__(
            self,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    def to_polyline(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Polyline` representation of
        the polygon.

        Args:
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`fiftyone.core.labels.Polyline`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Polyline(
            label=label,
            points=[points],
            closed=True,
            filled=True,
            attributes=attributes,
        )

    @classmethod
    def from_polyline(cls, frame_number, polyline, frame_size):
        """Creates a :class:`CVATVideoPolygon` from a
        :class:`fiftyone.core.labels.Polyline`.

        Args:
            frame_number: the frame number
            polyline: a :class:`fiftyone.core.labels.Polyline`
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATVideoPolygon`
        """
        label = polyline.label

        points = _get_single_polyline_points(polyline)
        points = cls._to_abs_points(points, frame_size)

        outside, occluded, keyframe, attributes = cls._parse_attributes(
            polyline
        )

        return cls(
            frame_number,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    @classmethod
    def from_polygon_dict(cls, label, d):
        """Creates a :class:`CVATVideoPolygon` from a ``<polygon>`` tag of a
        CVAT video annotation XML file.

        Args:
            label: the object label
            d: a dict representation of a ``<polygon>`` tag

        Returns:
            a :class:`CVATVideoPolygon`
        """
        frame = int(d["@frame"])
        points = cls._parse_cvat_points_str(d["@points"])
        outside, occluded, keyframe, attributes = cls._parse_anno_dict(d)
        return cls(
            frame,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )


class CVATVideoPolyline(CVATVideoAnno, HasCVATPoints):
    """A polyline in CVAT video format.

    Args:
        frame: the frame number
        label: the polyline label string
        points: a list of ``(x, y)`` pixel coordinates defining the vertices of
            the polyline
        outside (None): whether the polyline is truncated by the frame edge
        occluded (None): whether the polyline is occluded
        keyframe (None): whether the frame is a key frame
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self,
        frame,
        label,
        points,
        outside=None,
        occluded=None,
        keyframe=None,
        attributes=None,
    ):
        self.frame = frame
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATVideoAnno.__init__(
            self,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    def to_polyline(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Polyline` representation of
        the polyline.

        Args:
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`fiftyone.core.labels.Polyline`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Polyline(
            label=label,
            points=[points],
            closed=False,
            filled=False,
            attributes=attributes,
        )

    @classmethod
    def from_polyline(cls, frame_number, polyline, frame_size):
        """Creates a :class:`CVATVideoPolyline` from a
        :class:`fiftyone.core.labels.Polyline`.

        Args:
            frame_number: the frame number
            polyline: a :class:`fiftyone.core.labels.Polyline`
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATVideoPolyline`
        """
        label = polyline.label

        points = _get_single_polyline_points(polyline)
        points = cls._to_abs_points(points, frame_size)
        if points and polyline.closed:
            points.append(copy(points[0]))

        outside, occluded, keyframe, attributes = cls._parse_attributes(
            polyline
        )

        return cls(
            frame_number,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    @classmethod
    def from_polyline_dict(cls, label, d):
        """Creates a :class:`CVATVideoPolyline` from a ``<polyline>`` tag of a
        CVAT video annotation XML file.

        Args:
            label: the object label
            d: a dict representation of a ``<polyline>`` tag

        Returns:
            a :class:`CVATVideoPolyline`
        """
        frame = int(d["@frame"])
        points = cls._parse_cvat_points_str(d["@points"])
        outside, occluded, keyframe, attributes = cls._parse_anno_dict(d)
        return cls(
            frame,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )


class CVATVideoPoints(CVATVideoAnno, HasCVATPoints):
    """A set of keypoints in CVAT video format.

    Args:
        frame: the frame number
        label: the keypoints label string
        points: a list of ``(x, y)`` pixel coordinates defining the keypoints
        outside (None): whether the keypoints are truncated by the frame edge
        occluded (None): whether the keypoints are occluded
        keyframe (None): whether the frame is a key frame
        attributes (None): a list of :class:`CVATAttribute` instances
    """

    def __init__(
        self,
        frame,
        label,
        points,
        outside=None,
        occluded=None,
        keyframe=None,
        attributes=None,
    ):
        self.frame = frame
        self.label = label
        HasCVATPoints.__init__(self, points)
        CVATVideoAnno.__init__(
            self,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    def to_keypoint(self, frame_size):
        """Returns a :class:`fiftyone.core.labels.Keypoint` representation of
        the points.

        Args:
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`fiftyone.core.labels.Keypoint`
        """
        label = self.label
        points = self._to_rel_points(self.points, frame_size)
        attributes = self._to_attributes()
        return fol.Keypoint(label=label, points=points, attributes=attributes)

    @classmethod
    def from_keypoint(cls, frame_number, keypoint, frame_size):
        """Creates a :class:`CVATVideoPoints` from a
        :class:`fiftyone.core.labels.Keypoint`.

        Args:
            frame_number: the frame number
            keypoint: a :class:`fiftyone.core.labels.Keypoint`
            frame_size: the ``(width, height)`` of the video frames

        Returns:
            a :class:`CVATVideoPoints`
        """
        label = keypoint.label
        points = cls._to_abs_points(keypoint.points, frame_size)
        outside, occluded, keyframe, attributes = cls._parse_attributes(
            keypoint
        )
        return cls(
            frame_number,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )

    @classmethod
    def from_points_dict(cls, label, d):
        """Creates a :class:`CVATVideoPoints` from a ``<points>`` tag of a
        CVAT video annotation XML file.

        Args:
            label: the object label
            d: a dict representation of a ``<points>`` tag

        Returns:
            a :class:`CVATVideoPoints`
        """
        frame = int(d["@frame"])
        points = cls._parse_cvat_points_str(d["@points"])
        outside, occluded, keyframe, attributes = cls._parse_anno_dict(d)
        return cls(
            frame,
            label,
            points,
            outside=outside,
            occluded=occluded,
            keyframe=keyframe,
            attributes=attributes,
        )


class CVATAttribute(object):
    """An attribute in CVAT image format.

    Args:
        name: the attribute name
        value: the attribute value
    """

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def to_eta_attribute(self):
        """Returns an ``eta.core.data.Attribute`` representation of the
        attribute.

        Returns:
            an ``eta.core.data.Attribute``
        """
        if isinstance(self.value, bool):
            return etad.BooleanAttribute(self.name, self.value)

        if etau.is_numeric(self.value):
            return etad.NumericAttribute(self.name, self.value)

        return etad.CategoricalAttribute(self.name, self.value)

    def to_attribute(self):
        """Returns a :class:`fiftyone.core.labels.Attribute` representation of
        the attribute.

        Returns:
            a :class:`fiftyone.core.labels.Attribute`
        """
        if isinstance(self.value, bool):
            return fol.BooleanAttribute(value=self.value)

        if etau.is_numeric(self.value):
            return fol.NumericAttribute(value=self.value)

        return fol.CategoricalAttribute(value=self.value)


class CVATImageAnnotationWriter(object):
    """Class for writing annotations in CVAT image format.

    See :class:`fiftyone.types.dataset_types.CVATImageDataset` for format
    details.
    """

    def __init__(self):
        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(foc.RESOURCES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = environment.get_template(
            "cvat_image_annotation_template.xml"
        )

    def write(
        self, cvat_task_labels, cvat_images, xml_path, id=None, name=None
    ):
        """Writes the annotations to disk.

        Args:
            cvat_task_labels: a :class:`CVATTaskLabels` instance
            cvat_images: a list of :class:`CVATImage` instances
            xml_path: the path to write the annotations XML file
            id (None): an ID for the task
            name (None): a name for the task
        """
        now = datetime.now().isoformat()
        xml_str = self.template.render(
            {
                "id": id if id is not None else "",
                "name": name if name is not None else "",
                "size": len(cvat_images),
                "created": now,
                "updated": now,
                "labels": cvat_task_labels.labels,
                "dumped": now,
                "images": cvat_images,
            }
        )
        etau.write_file(xml_str, xml_path)


class CVATVideoAnnotationWriter(object):
    """Class for writing annotations in CVAT video format.

    See :class:`fiftyone.types.dataset_types.CVATVideoDataset` for format
    details.
    """

    def __init__(self):
        environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(foc.RESOURCES_DIR),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = environment.get_template(
            "cvat_video_interpolation_template.xml"
        )

    def write(
        self,
        cvat_task_labels,
        cvat_tracks,
        metadata,
        xml_path,
        id=None,
        name=None,
    ):
        """Writes the annotations to disk.

        Args:
            cvat_task_labels: a :class:`CVATTaskLabels` instance
            cvat_tracks: a list of :class:`CVATTrack` instances
            metadata: the :class:`fiftyone.core.metadata.VideoMetadata`
                instance for the video
            xml_path: the path to write the annotations XML file
            id (None): an ID for the task
            name (None): a name for the task
        """
        now = datetime.now().isoformat()
        xml_str = self.template.render(
            {
                "id": id if id is not None else "",
                "name": name if name is not None else "",
                "size": metadata.total_frame_count,
                "created": now,
                "updated": now,
                "width": metadata.frame_width,
                "height": metadata.frame_height,
                "labels": cvat_task_labels.labels,
                "dumped": now,
                "tracks": cvat_tracks,
            }
        )
        etau.write_file(xml_str, xml_path)


def load_cvat_image_annotations(xml_path):
    """Loads the CVAT image annotations from the given XML file.

    See :class:`fiftyone.types.dataset_types.CVATImageDataset` for format
    details.

    Args:
        xml_path: the path to the annotations XML file

    Returns:
        a tuple of

        -   info: a dict of dataset info
        -   cvat_task_labels: a :class:`CVATTaskLabels` instance
        -   cvat_images: a list of :class:`CVATImage` instances
    """
    d = fou.load_xml_as_json_dict(xml_path)
    annotations = d.get("annotations", {})

    # Verify version
    version = annotations.get("version", None)
    if version is None:
        logger.warning("No version tag found; assuming version 1.1")
    elif version != "1.1":
        logger.warning(
            "Only version 1.1 is explicitly supported; found %s. Trying to "
            "load assuming version 1.1 format",
            version,
        )

    # Load meta
    meta = annotations.get("meta", {})

    # Load task labels
    task = meta.get("task", {})
    labels_dict = task.get("labels", {})
    cvat_task_labels = CVATTaskLabels.from_labels_dict(labels_dict)

    # Load annotations
    image_dicts = _ensure_list(annotations.get("image", []))
    cvat_images = [CVATImage.from_image_dict(id) for id in image_dicts]

    # Load dataset info
    info = {"task_labels": cvat_task_labels.labels}
    if "created" in task:
        info["created"] = task["created"]

    if "updated" in task:
        info["updated"] = task["updated"]

    if "dumped" in meta:
        info["dumped"] = meta["dumped"]

    return info, cvat_task_labels, cvat_images


def load_cvat_video_annotations(xml_path):
    """Loads the CVAT video annotations from the given XML file.

    See :class:`fiftyone.types.dataset_types.CVATVideoDataset` for format
    details.

    Args:
        xml_path: the path to the annotations XML file

    Returns:
        a tuple of

        -   info: a dict of dataset info
        -   cvat_task_labels: a :class:`CVATTaskLabels` instance
        -   cvat_tracks: a list of :class:`CVATTrack` instances
    """
    d = fou.load_xml_as_json_dict(xml_path)
    annotations = d.get("annotations", {})

    # Verify version
    version = annotations.get("version", None)
    if version is None:
        logger.warning("No version tag found; assuming version 1.1")
    elif version != "1.1":
        logger.warning(
            "Only version 1.1 is explicitly supported; found %s. Trying to "
            "load assuming version 1.1 format",
            version,
        )

    # Load meta
    meta = annotations.get("meta", {})

    # Load task labels
    task = meta.get("task", {})
    labels_dict = task.get("labels", {})
    cvat_task_labels = CVATTaskLabels.from_labels_dict(labels_dict)

    # Load annotations
    track_dicts = _ensure_list(annotations.get("track", []))
    if track_dicts:
        original_size = task["original_size"]
        frame_size = (
            int(original_size["width"]),
            int(original_size["height"]),
        )
        cvat_tracks = [
            CVATTrack.from_track_dict(td, frame_size) for td in track_dicts
        ]
    else:
        cvat_tracks = []

    # Load dataset info
    info = {"task_labels": cvat_task_labels.labels}
    if "created" in task:
        info["created"] = task["created"]

    if "updated" in task:
        info["updated"] = task["updated"]

    if "dumped" in meta:
        info["dumped"] = meta["dumped"]

    return info, cvat_task_labels, cvat_tracks


def _cvat_tracks_to_frames_dict(cvat_tracks):
    frames = defaultdict(dict)
    for cvat_track in cvat_tracks:
        labels = cvat_track.to_labels()
        for frame_number, label in labels.items():
            frame = frames[frame_number]

            if isinstance(label, fol.Detection):
                if "detections" not in frame:
                    frame["detections"] = fol.Detections()

                frame["detections"].detections.append(label)
            elif isinstance(label, fol.Polyline):
                if "polylines" not in frame:
                    frame["polylines"] = fol.Polylines()

                frame["polylines"].polylines.append(label)
            elif isinstance(label, fol.Keypoint):
                if "keypoints" not in frame:
                    frame["keypoints"] = fol.Keypoints()

                frame["keypoints"].keypoints.append(label)

    return frames


def _frames_to_cvat_tracks(frames, frame_size):
    labels_map = defaultdict(dict)
    no_index_map = defaultdict(list)
    found_label = False

    def process_label(label, frame_number):
        if label.index is not None:
            labels_map[label.index][frame_number] = label
        else:
            no_index_map[frame_number].append(label)

    # Convert from per-frame to per-object tracks
    for frame_number, frame_dict in frames.items():
        for _, value in frame_dict.items():
            if isinstance(value, (fol.Detection, fol.Polyline, fol.Keypoint)):
                found_label = True
                process_label(value, frame_number)
            elif isinstance(value, fol.Detections):
                found_label = True
                for detection in value.detections:
                    process_label(detection, frame_number)
            elif isinstance(value, fol.Polylines):
                found_label = True
                for polyline in value.polylines:
                    process_label(polyline, frame_number)
            elif isinstance(value, fol.Keypoints):
                found_label = True
                for keypoint in value.keypoints:
                    process_label(keypoint, frame_number)
            elif value is not None:
                msg = "Ignoring unsupported label type '%s'" % value.__class__
                warnings.warn(msg)

    if not found_label:
        return None  # unlabeled

    cvat_tracks = []

    # Generate object tracks
    max_index = -1
    for index in sorted(labels_map):
        max_index = max(index, max_index)
        labels = labels_map[index]
        cvat_track = CVATTrack.from_labels(index, labels, frame_size)
        cvat_tracks.append(cvat_track)

    # Generate single tracks for detections with no `index`
    index = max_index
    for frame_number, labels in no_index_map.items():
        for label in labels:
            index += 1
            cvat_track = CVATTrack.from_labels(
                index, {frame_number: label}, frame_size
            )
            cvat_tracks.append(cvat_track)

    return cvat_tracks


def _get_single_polyline_points(polyline):
    num_polylines = len(polyline.points)
    if num_polylines == 0:
        return []

    if num_polylines > 0:
        msg = (
            "Found polyline with more than one shape; only the first shape "
            "will be stored in CVAT format"
        )
        warnings.warn(msg)

    return polyline.points[0]


def _ensure_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]
