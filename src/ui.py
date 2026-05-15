from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass
class UIState:
    selected_template_index: int = 0
    countdown_seconds: int = 3


class BoothUI(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = UIState()
        self.setWindowTitle("ซุ้มถ่ายภาพอัตโนมัติ")
        self.stack = QStackedWidget()

        self.welcome_page = self._build_welcome_page()
        self.template_page = self._build_template_page()
        self.camera_page = self._build_camera_page()
        self.countdown_page = self._build_countdown_page()
        self.processing_page = self._build_processing_page()
        self.result_page = self._build_result_page()

        for p in [
            self.welcome_page,
            self.template_page,
            self.camera_page,
            self.countdown_page,
            self.processing_page,
            self.result_page,
        ]:
            self.stack.addWidget(p)

        root = QVBoxLayout()
        root.addWidget(self.stack)
        self.setLayout(root)

    def _title(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 44px; font-weight: bold;")
        return lbl

    def _big_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(80)
        btn.setStyleSheet("font-size: 34px; padding: 18px;")
        return btn

    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addStretch()
        lay.addWidget(self._title("ยินดีต้อนรับสู่ซุ้มถ่ายภาพนักเรียน"))
        self.welcome_hint = QLabel("แบมือเพื่อเริ่ม หรือกดปุ่มเริ่มใช้งาน")
        self.welcome_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.welcome_hint.setStyleSheet("font-size: 30px;")
        lay.addWidget(self.welcome_hint)
        self.btn_start = self._big_btn("เริ่มใช้งาน")
        lay.addWidget(self.btn_start)
        lay.addStretch()
        return page

    def _build_template_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(self._title("เลือกธีมรูปภาพ"))
        self.template_name = QLabel("ยังไม่ได้เลือก")
        self.template_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.template_name.setStyleSheet("font-size: 30px;")
        lay.addWidget(self.template_name)

        self.template_preview = QLabel("ตัวอย่างธีม")
        self.template_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.template_preview.setStyleSheet("font-size: 28px; border: 2px solid #777;")
        self.template_preview.setMinimumHeight(360)
        lay.addWidget(self.template_preview)

        hint = QLabel("ปัดซ้าย/ขวาเพื่อเปลี่ยนธีม หรือกดปุ่มด้านล่าง")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("font-size: 24px;")
        lay.addWidget(hint)

        row = QHBoxLayout()
        self.btn_prev_template = self._big_btn("◀ ธีมก่อนหน้า")
        self.btn_next_template = self._big_btn("ธีมถัดไป ▶")
        row.addWidget(self.btn_prev_template)
        row.addWidget(self.btn_next_template)
        lay.addLayout(row)

        self.btn_to_camera = self._big_btn("ยืนยันธีมและไปหน้ากล้อง")
        self.btn_back_home = self._big_btn("ย้อนกลับ")
        lay.addWidget(self.btn_to_camera)
        lay.addWidget(self.btn_back_home)
        return page

    def _build_camera_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(self._title("จัดท่าทางหน้ากล้อง"))
        self.camera_feed = QLabel("กำลังเตรียมกล้อง...")
        self.camera_feed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_feed.setMinimumHeight(480)
        self.camera_feed.setStyleSheet("font-size: 24px; border: 2px solid #777;")
        lay.addWidget(self.camera_feed)
        self.camera_status = QLabel("ชูนิ้วโป้งเพื่อถ่ายภาพ | กำมือเพื่อย้อนกลับ")
        self.camera_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_status.setStyleSheet("font-size: 24px;")
        lay.addWidget(self.camera_status)
        row = QHBoxLayout()
        self.btn_take_photo = self._big_btn("ถ่ายภาพ")
        self.btn_cancel_camera = self._big_btn("ย้อนกลับ")
        row.addWidget(self.btn_take_photo)
        row.addWidget(self.btn_cancel_camera)
        lay.addLayout(row)
        return page

    def _build_countdown_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(self._title("เตรียมตัวถ่ายภาพ"))
        self.countdown_label = QLabel("3")
        self.countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdown_label.setStyleSheet("font-size: 120px; font-weight: bold;")
        lay.addWidget(self.countdown_label)
        return page

    def _build_processing_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(self._title("กำลังประมวลผลรูปภาพ กรุณารอสักครู่"))
        return page

    def _build_result_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(self._title("เสร็จเรียบร้อย"))
        self.result_image = QLabel("รูปภาพผลลัพธ์")
        self.result_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_image.setMinimumHeight(420)
        self.result_image.setStyleSheet("font-size: 24px; border: 2px solid #777;")
        lay.addWidget(self.result_image)
        self.result_code = QLabel("รหัสรูปภาพ: -")
        self.result_code.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_code.setStyleSheet("font-size: 36px; font-weight: bold;")
        lay.addWidget(self.result_code)
        self.qr_placeholder = QLabel("พื้นที่ QR: (จะเพิ่มภายหลัง)")
        self.qr_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_placeholder.setStyleSheet("font-size: 24px;")
        lay.addWidget(self.qr_placeholder)
        self.btn_finish = self._big_btn("เสร็จสิ้นและกลับหน้าแรก")
        lay.addWidget(self.btn_finish)
        return page

    def show_page(self, name: str) -> None:
        mapping = {
            "welcome": self.welcome_page,
            "template": self.template_page,
            "camera": self.camera_page,
            "countdown": self.countdown_page,
            "processing": self.processing_page,
            "result": self.result_page,
        }
        self.stack.setCurrentWidget(mapping[name])

    def set_template_preview(self, template_name: str, image_path: str) -> None:
        self.template_name.setText(f"ธีมที่เลือก: {template_name}")
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.template_preview.setText("ไม่พบรูปตัวอย่างธีม")
            return
        self.template_preview.setPixmap(pixmap.scaled(640, 360, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def set_result(self, image_code: str, output_path: str) -> None:
        self.result_code.setText(f"รหัสรูปภาพ: {image_code}")
        pixmap = QPixmap(output_path)
        if pixmap.isNull():
            self.result_image.setText("ไม่พบรูปผลลัพธ์")
            return
        self.result_image.setPixmap(pixmap.scaled(740, 420, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
