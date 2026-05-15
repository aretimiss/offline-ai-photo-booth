from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import cv2
from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QApplication

from .camera import CameraService
from .face_swap import FaceSwapEngine
from .gesture import GestureEvent, GestureRecognizer
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

GESTURE_TO_THAI = {
    "none": "-",
    "open_palm": "แบมือ",
    "thumbs_up": "ยกนิ้วโป้ง",
    "swipe_left": "ปัดซ้าย",
    "swipe_right": "ปัดขวา",
    "fist": "กำมือ",
}


def load_settings(path: str | Path = "config/settings.json") -> dict:
    p = Path(path)
    if not p.exists():
        p = Path("config/settings.example.json")
    return json.loads(p.read_text(encoding="utf-8"))


class PhotoBoothController:
    def __init__(self, settings: dict, app: QApplication) -> None:
        self.settings = settings
        self.app = app
        self.ui = BoothUI()
        self.ui.showFullScreen()

        self.template_manager = TemplateManager(settings["templates_json"])
        self.template_manager.load()
        self.current_template_index = 0

        self.camera = CameraService(camera_index=settings.get("camera_index", 0))
        self.camera_ok = self.camera.start()
        self.demo_mode = not self.camera_ok
        self.gesture = GestureRecognizer() if self.camera_ok else None

        self.face_swap = FaceSwapEngine(watermark_text=settings.get("watermark_text"))
        self.uploader = UploadQueue(settings["queue_file"], settings["drive_remote_path"])
        self.captures_dir = Path(settings["captures_dir"]); self.captures_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir = Path(settings["outputs_dir"]); self.outputs_dir.mkdir(parents=True, exist_ok=True)

        self.last_triggered_at = 0.0
        self.cooldown_sec = 1.0
        self.hold_sec = 0.5
        self.hold_name = "none"
        self.hold_started_at = 0.0
        self.latest_frame = None

        self._wire_events()
        self.update_template_preview()
        self.go_welcome("เริ่มต้นระบบ")

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_frame)
        self.timer.start(33)
        self.app.installEventFilter(self)

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.KeyPress:
            self.handle_key(event)
            return True
        return False

    def handle_key(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Space:
            self.trigger_primary_action("แป้นพิมพ์: Space")
        elif key == Qt.Key.Key_Left:
            self.prev_template("แป้นพิมพ์: Left")
        elif key == Qt.Key.Key_Right:
            self.next_template("แป้นพิมพ์: Right")
        elif key == Qt.Key.Key_Backspace:
            self.back_action("แป้นพิมพ์: Backspace")
        elif key == Qt.Key.Key_R:
            self.go_welcome("แป้นพิมพ์: R รีเซ็ต")

    def _wire_events(self) -> None:
        self.ui.btn_start.clicked.connect(lambda: self.go_template("ปุ่ม: เริ่มใช้งาน"))
        self.ui.btn_welcome_back.clicked.connect(lambda: self.go_welcome("ปุ่ม: รีเซ็ต"))
        self.ui.btn_prev_template.clicked.connect(lambda: self.prev_template("ปุ่ม: ธีมก่อนหน้า"))
        self.ui.btn_next_template.clicked.connect(lambda: self.next_template("ปุ่ม: ธีมถัดไป"))
        self.ui.btn_back_home.clicked.connect(lambda: self.go_welcome("ปุ่ม: ย้อนกลับ"))
        self.ui.btn_to_camera.clicked.connect(lambda: self.go_camera("ปุ่ม: ไปหน้ากล้อง"))
        self.ui.btn_take_photo.clicked.connect(lambda: self.capture_flow(self.latest_frame, "ปุ่ม: ถ่ายภาพ"))
        self.ui.btn_cancel_camera.clicked.connect(lambda: self.go_template("ปุ่ม: ย้อนกลับจากกล้อง"))
        self.ui.btn_cancel_countdown.clicked.connect(lambda: self.go_camera("ปุ่ม: ยกเลิกนับถอยหลัง"))
        self.ui.btn_back_processing.clicked.connect(lambda: self.go_welcome("ปุ่ม: กลับหน้าแรก"))
        self.ui.btn_finish.clicked.connect(lambda: self.go_welcome("ปุ่ม: เสร็จสิ้น"))
        self.ui.btn_result_back.clicked.connect(lambda: self.go_template("ปุ่ม: กลับเลือกธีม"))

    @property
    def page_name(self) -> str:
        w = self.ui.stack.currentWidget()
        if w == self.ui.welcome_page:
            return "welcome"
        if w == self.ui.template_page:
            return "template"
        if w == self.ui.camera_page:
            return "camera"
        if w == self.ui.countdown_page:
            return "countdown"
        if w == self.ui.processing_page:
            return "processing"
        return "result"

    @property
    def current_template(self):
        return self.template_manager.get(self.current_template_index)

    def go_welcome(self, reason: str = "") -> None:
        self.ui.show_page("welcome"); logger.info("หน้า: ต้อนรับ | %s", reason)

    def go_template(self, reason: str = "") -> None:
        self.update_template_preview(); self.ui.show_page("template"); logger.info("หน้า: เลือกธีม | %s", reason)

    def go_camera(self, reason: str = "") -> None:
        self.ui.show_page("camera"); logger.info("หน้า: กล้อง | %s", reason)
        if self.demo_mode:
            self.ui.camera_status.setText("ไม่พบกล้อง: ใช้โหมดเดโม (กดปุ่มถ่ายภาพได้)")

    def prev_template(self, reason: str = "") -> None:
        self.current_template_index -= 1; self.update_template_preview(); logger.info("เปลี่ยนธีม: %s | %s", self.current_template.name, reason)

    def next_template(self, reason: str = "") -> None:
        self.current_template_index += 1; self.update_template_preview(); logger.info("เปลี่ยนธีม: %s | %s", self.current_template.name, reason)

    def update_template_preview(self) -> None:
        t = self.current_template
        self.ui.set_template_preview(t.name, t.image_path)

    def trigger_primary_action(self, source: str) -> None:
        if self.page_name in {"welcome"}:
            self.go_template(source)
        elif self.page_name in {"template"}:
            self.go_camera(source)
        elif self.page_name in {"camera"}:
            self.capture_flow(self.latest_frame, source)
        elif self.page_name in {"result"}:
            self.go_welcome(source)

    def back_action(self, source: str) -> None:
        if self.page_name == "camera":
            self.go_template(source)
        elif self.page_name == "template":
            self.go_welcome(source)
        elif self.page_name == "result":
            self.go_template(source)
        else:
            self.go_welcome(source)

    def on_frame(self) -> None:
        frame = self.camera.read_frame() if self.camera_ok else None
        if frame is not None:
            self.latest_frame = frame.copy()
        if self.page_name != "camera":
            return
        if frame is None:
            self.ui.camera_feed.setText("โหมดเดโม: ไม่มีกล้อง\nกด 'ถ่ายภาพ' เพื่อทดสอบระบบ")
            self.ui.set_gesture_debug(False, "-", 0.0)
            return

        evt = self.gesture.detect(frame) if self.gesture is not None else GestureEvent(False, "none", 0.0)
        self.ui.set_gesture_debug(evt.hand_detected, GESTURE_TO_THAI[evt.name], evt.confidence)
        logger.info("gesture_event | พบมือ=%s | gesture=%s | conf=%.2f | page=%s", evt.hand_detected, evt.name, evt.confidence, self.page_name)
        self._handle_gesture_with_hold(evt)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qimg = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.ui.camera_feed.setPixmap(QPixmap.fromImage(qimg).scaled(920, 520, Qt.AspectRatioMode.KeepAspectRatio))

    def _handle_gesture_with_hold(self, evt: GestureEvent) -> None:
        now = time.monotonic()
        if now - self.last_triggered_at < self.cooldown_sec or evt.name == "none":
            return
        if evt.name != self.hold_name:
            self.hold_name = evt.name
            self.hold_started_at = now
            return
        if now - self.hold_started_at < self.hold_sec:
            return

        action = "ไม่มี"
        if evt.name == "thumbs_up":
            self.capture_flow(self.latest_frame, "ท่ามือ: ยกนิ้วโป้ง")
            action = "ถ่ายภาพ"
        elif evt.name == "fist":
            self.back_action("ท่ามือ: กำมือ")
            action = "ย้อนกลับ"
        elif evt.name == "swipe_left":
            self.prev_template("ท่ามือ: ปัดซ้าย")
            action = "ธีมก่อนหน้า"
        elif evt.name == "swipe_right":
            self.next_template("ท่ามือ: ปัดขวา")
            action = "ธีมถัดไป"
        elif evt.name == "open_palm":
            self.trigger_primary_action("ท่ามือ: แบมือ")
            action = "ไปต่อ"

        self.last_triggered_at = now
        logger.info("gesture_trigger | gesture=%s | page=%s | action=%s", evt.name, self.page_name, action)

    def capture_flow(self, existing_frame=None, reason: str = "") -> None:
        logger.info("เริ่มถ่ายภาพ | %s", reason)
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
        frame = existing_frame
        if frame is None and self.camera_ok:
            frame = self.camera.read_frame()
        if frame is None:
            frame = 255 * cv2.UMat(720, 1280, cv2.CV_8UC3).get()
            cv2.putText(frame, "DEMO", (500, 360), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 8)

        raw_path = self.captures_dir / output_filename(generate_image_code())
        cv2.imwrite(str(raw_path), frame)
        out_code = generate_image_code()
        out_path = self.outputs_dir / output_filename(out_code)

        self.face_swap.swap_face(str(raw_path), self.current_template.image_path, str(out_path))
        safe_delete(raw_path)
        self.uploader.enqueue(QueueItem(image_code=out_code, local_path=str(out_path)))
        if self.uploader.internet_available():
            self.uploader.sync_pending()
        self.ui.set_result(out_code, str(out_path))
        self.ui.show_page("result")
        logger.info("สร้างรูปสำเร็จ | รหัส=%s", out_code)

    def close(self) -> None:
        if self.gesture is not None:
            self.gesture.close()
        self.camera.stop()


def main() -> None:
    app = QApplication(sys.argv)
    controller = PhotoBoothController(load_settings(), app)
    app.aboutToQuit.connect(controller.close)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
