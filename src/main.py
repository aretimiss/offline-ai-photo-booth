from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import cv2
from PySide6.QtCore import QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from .camera import CameraService
from .face_swap import FaceSwapEngine
from .gesture import GestureRecognizer
from .privacy import generate_image_code, output_filename, safe_delete
from .template_manager import TemplateManager
from .ui import BoothUI
from .uploader import QueueItem, UploadQueue


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("logs/app.log", encoding="utf-8")],
)
logger = logging.getLogger("photo_booth")


def load_settings(path: str | Path = "config/settings.json") -> dict:
    settings_path = Path(path)
    if not settings_path.exists():
        settings_path = Path("config/settings.example.json")
    with settings_path.open("r", encoding="utf-8") as f:
        return json.load(f)


class PhotoBoothController:
    def __init__(self, settings: dict) -> None:
        self.settings = settings
        self.ui = BoothUI()
        self.ui.showFullScreen()

        self.template_manager = TemplateManager(settings["templates_json"])
        self.templates = self.template_manager.load()
        if not self.templates:
            raise RuntimeError("No templates configured")

        self.current_template_index = 0
        self.camera = CameraService(camera_index=settings.get("camera_index", 0))
        self.camera_ok = self.camera.start()
        self.demo_mode = not self.camera_ok

        self.gesture = GestureRecognizer() if self.camera_ok else None
        self.face_swap = FaceSwapEngine(watermark_text=settings.get("watermark_text"))
        self.uploader = UploadQueue(settings["queue_file"], settings["drive_remote_path"])

        self.captures_dir = Path(settings["captures_dir"])
        self.outputs_dir = Path(settings["outputs_dir"])
        self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        self._wire_events()
        self.update_template_preview()
        self.go_welcome()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_frame)
        self.timer.start(30)

        logger.info("เริ่มระบบซุ้มถ่ายภาพ | โหมดเดโม=%s", self.demo_mode)

    def _wire_events(self) -> None:
        self.ui.btn_start.clicked.connect(self.go_template)
        self.ui.btn_prev_template.clicked.connect(self.prev_template)
        self.ui.btn_next_template.clicked.connect(self.next_template)
        self.ui.btn_back_home.clicked.connect(self.go_welcome)
        self.ui.btn_to_camera.clicked.connect(self.go_camera)
        self.ui.btn_take_photo.clicked.connect(self.capture_flow)
        self.ui.btn_cancel_camera.clicked.connect(self.go_template)
        self.ui.btn_finish.clicked.connect(self.go_welcome)

    def go_welcome(self) -> None:
        logger.info("หน้า: ต้อนรับ")
        self.ui.show_page("welcome")

    def go_template(self) -> None:
        logger.info("หน้า: เลือกธีม")
        self.update_template_preview()
        self.ui.show_page("template")

    def go_camera(self) -> None:
        logger.info("หน้า: กล้อง")
        self.ui.show_page("camera")
        if self.demo_mode:
            self.ui.camera_status.setText("ไม่พบกล้อง: ใช้โหมดเดโม (กดปุ่มถ่ายภาพได้)")

    def prev_template(self) -> None:
        self.current_template_index -= 1
        self.update_template_preview()
        logger.info("เปลี่ยนธีม: %s", self.current_template.name)

    def next_template(self) -> None:
        self.current_template_index += 1
        self.update_template_preview()
        logger.info("เปลี่ยนธีม: %s", self.current_template.name)

    @property
    def current_template(self):
        return self.template_manager.get(self.current_template_index)

    def update_template_preview(self) -> None:
        t = self.current_template
        self.ui.set_template_preview(t.name, t.image_path)

    def on_frame(self) -> None:
        if self.ui.stack.currentWidget() != self.ui.camera_page:
            return

        frame = self.camera.read_frame() if self.camera_ok else None
        if frame is None:
            self.ui.camera_feed.setText("โหมดเดโม: ไม่มีกล้อง\nกด 'ถ่ายภาพ' เพื่อทดสอบระบบ")
            return

        if self.gesture is not None:
            evt = self.gesture.detect(frame)
            if evt.name == "thumbs_up":
                self.capture_flow(frame)
            elif evt.name == "fist":
                self.go_template()
            elif evt.name == "swipe_left":
                self.prev_template()
            elif evt.name == "swipe_right":
                self.next_template()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.ui.camera_feed.setPixmap(QPixmap.fromImage(qimg).scaled(900, 520))

    def capture_flow(self, existing_frame=None) -> None:
        logger.info("เริ่มขั้นตอนถ่ายภาพ")
        self.ui.show_page("countdown")
        self.countdown = 3
        self.countdown_timer = QTimer()

        def tick() -> None:
            self.ui.countdown_label.setText(str(self.countdown))
            if self.countdown == 0:
                self.countdown_timer.stop()
                self.process_capture(existing_frame)
            self.countdown -= 1

        self.countdown_timer.timeout.connect(tick)
        tick()
        self.countdown_timer.start(1000)

    def process_capture(self, existing_frame=None) -> None:
        self.ui.show_page("processing")
        logger.info("กำลังประมวลผลภาพ")

        frame = existing_frame
        if frame is None and self.camera_ok:
            frame = self.camera.read_frame()
        if frame is None:
            frame = 255 * cv2.UMat(720, 1280, cv2.CV_8UC3).get()
            cv2.putText(frame, "DEMO", (500, 360), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 8)

        raw_code = generate_image_code()
        raw_path = self.captures_dir / output_filename(raw_code)
        cv2.imwrite(str(raw_path), frame)

        out_code = generate_image_code()
        out_path = self.outputs_dir / output_filename(out_code)

        self.face_swap.swap_face(str(raw_path), self.current_template.image_path, str(out_path))
        safe_delete(raw_path)

        self.uploader.enqueue(QueueItem(image_code=out_code, local_path=str(out_path)))
        if self.uploader.internet_available():
            logger.info("ตรวจพบอินเทอร์เน็ต: เริ่มซิงก์ไฟล์")
            self.uploader.sync_pending()
        else:
            logger.info("ออฟไลน์: เก็บไฟล์ไว้ในคิว")

        logger.info("เสร็จสิ้น | รหัสรูป=%s", out_code)
        self.ui.set_result(out_code, str(out_path))
        self.ui.show_page("result")

    def close(self) -> None:
        if self.gesture is not None:
            self.gesture.close()
        self.camera.stop()


def main() -> None:
    settings = load_settings()
    app = QApplication(sys.argv)
    controller = PhotoBoothController(settings)
    app.aboutToQuit.connect(controller.close)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
