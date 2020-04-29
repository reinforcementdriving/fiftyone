import os
import sys
from eta.core.image import ImageLabels
from eta.core.video import VideoLabels

in_file = sys.argv[1]
out_dir = sys.argv[2]
if not os.path.isdir(out_dir):
    os.mkdir(out_dir)

video_labels = VideoLabels.from_json(in_file)
for index, frame in video_labels.frames.items():
    ImageLabels.from_frame_labels(frame).write_json(
        os.path.join(out_dir, "%04d.json" % index)
    )
