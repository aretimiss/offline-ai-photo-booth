from __future__ import annotations

from pathlib import Path

import cv2


class FaceSwapEngine:
    """Mock local face-swap engine for v1."""

    def __init__(self, watermark_text: str | None = None) -> None:
        self.watermark_text = watermark_text

    def swap_face(self, source_face_path: str, template_image_path: str, output_path: str) -> str:
        source = cv2.imread(source_face_path)
        template = cv2.imread(template_image_path)

        if source is None:
            raise ValueError(f"Could not read source face: {source_face_path}")
        if template is None:
            raise ValueError(f"Could not read template image: {template_image_path}")

        sh, sw = source.shape[:2]
        th, tw = template.shape[:2]

        target_w = max(1, int(tw * 0.35))
        target_h = max(1, int(sh * (target_w / sw)))
        resized_face = cv2.resize(source, (target_w, target_h))

        y1 = max(0, int(th * 0.25))
        x1 = max(0, int((tw - target_w) / 2))
        y2 = min(th, y1 + target_h)
        x2 = min(tw, x1 + target_w)

        overlay = template.copy()
        overlay[y1:y2, x1:x2] = resized_face[0 : y2 - y1, 0 : x2 - x1]

        if self.watermark_text:
            cv2.putText(
                overlay,
                self.watermark_text,
                (20, th - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(output_path, overlay)
        return output_path
