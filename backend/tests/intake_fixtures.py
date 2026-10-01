"""Small datasets in every format doc 136 imports, written to a folder for a test."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

W, H = 64, 48


def square_counts() -> list[int]:
    import numpy as np

    from app.datasets.rle import rle_encode

    mask = np.zeros((H, W), dtype=bool)
    mask[1:6, 1:6] = True
    return rle_encode(mask)[0]


def compress(counts: list[int]) -> str:
    """pycocotools' `rleToString`, the reference the decoder is checked against."""
    out = []
    for i, count in enumerate(counts):
        value = count - counts[i - 2] if i > 2 else count
        more = True
        while more:
            chunk = value & 0x1F
            value >>= 5
            more = value != -1 if chunk & 0x10 else value != 0
            if more:
                chunk |= 0x20
            out.append(chr(chunk + 48))
    return "".join(out)


def picture(path: Path, width: int = W, height: int = H) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), (90, 120, 150)).save(path)
    return path


def coco(root: Path) -> Path:
    """train/ and valid/ splits; a box, a polygon, a compressed-RLE mask, a background."""
    for split, names in (("train", ["a.jpg", "b.jpg"]), ("valid", ["c.jpg"])):
        for name in names:
            picture(root / split / name)
    train = {
        "images": [
            {"id": 1, "file_name": "a.jpg", "width": W, "height": H},
            {"id": 2, "file_name": "b.jpg", "width": W, "height": H},
        ],
        "categories": [
            {"id": 0, "name": "Signals"},
            {"id": 1, "name": "signal"},
            {"id": 2, "name": "person"},
        ],
        "annotations": [
            {"id": 1, "image_id": 1, "category_id": 1, "bbox": [4, 4, 10, 8]},
            {
                "id": 2,
                "image_id": 1,
                "category_id": 2,
                "bbox": [20, 10, 10, 10],
                "segmentation": [[20, 10, 30, 10, 30, 20, 20, 20]],
            },
            # pycocotools' compressed string form of a square mask.
            {
                "id": 3,
                "image_id": 2,
                "category_id": 2,
                "bbox": [1, 1, 5, 5],
                "segmentation": {"size": [H, W], "counts": compress(square_counts())},
            },
        ],
    }
    (root / "train" / "_annotations.coco.json").write_text(json.dumps(train))
    valid = {
        "images": [{"id": 1, "file_name": "c.jpg", "width": W, "height": H}],
        "categories": [{"id": 1, "name": "signal"}],
        "annotations": [],
    }
    (root / "valid" / "_annotations.coco.json").write_text(json.dumps(valid))
    picture(root / "train" / "extra.jpg")  # in no annotation file
    return root


def yolo(root: Path) -> Path:
    for name in ("a", "b", "c"):
        picture(root / "images" / "train" / f"{name}.jpg")
    labels = root / "labels" / "train"
    labels.mkdir(parents=True)
    (labels / "a.txt").write_text("0 0.5 0.5 0.25 0.5\n1 0.1 0.1 0.3 0.1 0.3 0.3 0.1 0.3\n")
    (labels / "b.txt").write_text("1 0.25 0.25 0.1 0.1\n")
    (root / "data.yaml").write_text("path: .\ntrain: images/train\nnames:\n  0: car\n  1: person\n")
    return root  # c.jpg has no label file: a background picture


def voc(root: Path) -> Path:
    picture(root / "JPEGImages" / "x.jpg")
    (root / "Annotations").mkdir(parents=True)
    (root / "Annotations" / "x.xml").write_text(
        f"<annotation><filename>x.jpg</filename><size><width>{W}</width><height>{H}</height>"
        "</size><object><name>dog</name><bndbox><xmin>5</xmin><ymin>6</ymin><xmax>25</xmax>"
        "<ymax>30</ymax></bndbox></object></annotation>"
    )
    return root


def openlabel(root: Path) -> Path:
    picture(root / "rgb_center" / "000.png")
    picture(root / "rgb_center" / "001.png")
    document = {
        "openlabel": {
            "metadata": {"schema_version": "1.0.0"},
            "streams": {"rgb_center": {"type": "camera"}, "lidar": {"type": "lidar"}},
            "objects": {"o1": {"type": "person"}, "o2": {"type": "track"}},
            "frames": {
                str(i): {
                    "frame_properties": {
                        "streams": {"rgb_center": {"uri": f"/rgb_center/00{i}.png"}}
                    },
                    "objects": {
                        "o1": {
                            "object_data": {
                                "bbox": [
                                    {"val": [20, 20, 10, 12], "coordinate_system": "rgb_center"}
                                ]
                            }
                        },
                    },
                }
                for i in (0, 1)
            },
        }
    }
    (root / "seq_labels.json").write_text(json.dumps(document))
    return root


def pictures_only(root: Path) -> Path:
    for i in range(3):
        picture(root / f"p{i}.png")
    return root


def video(path: Path, frames: int = 12) -> Path:
    import av
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = W, H, "yuv420p"
        for i in range(frames):
            array = np.full((H, W, 3), i * 15 % 255, dtype=np.uint8)
            for packet in stream.encode(av.VideoFrame.from_ndarray(array, format="rgb24")):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return path
