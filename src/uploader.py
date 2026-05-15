from __future__ import annotations

import json
import socket
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path


@dataclass
class QueueItem:
    image_code: str
    local_path: str
    status: str = "pending"
    created_at: str = datetime.now(UTC).isoformat()
    last_error: str = ""


class UploadQueue:
    def __init__(self, queue_file: str | Path, remote_path: str) -> None:
        self.queue_file = Path(queue_file)
        self.remote_path = remote_path
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.queue_file.exists():
            self._save([])

    def _load(self) -> list[dict]:
        with self.queue_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, items: list[dict]) -> None:
        with self.queue_file.open("w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)

    def enqueue(self, item: QueueItem) -> None:
        items = self._load()
        items.append(asdict(item))
        self._save(items)

    def internet_available(self, host: str = "8.8.8.8", port: int = 53, timeout: float = 2.0) -> bool:
        try:
            socket.setdefaulttimeout(timeout)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
            return True
        except OSError:
            return False

    def sync_pending(self) -> None:
        items = self._load()
        changed = False

        for item in items:
            if item["status"] == "uploaded":
                continue
            local_path = item["local_path"]
            try:
                subprocess.run(
                    ["rclone", "copy", local_path, self.remote_path],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                item["status"] = "uploaded"
                item["last_error"] = ""
                changed = True
            except Exception as exc:  # noqa: BLE001
                item["status"] = "pending"
                item["last_error"] = str(exc)
                changed = True

        if changed:
            self._save(items)
