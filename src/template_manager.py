from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Template:
    id: str
    name: str
    image_path: str
    description: str = ""


class TemplateManager:
    def __init__(self, template_json_path: str | Path) -> None:
        self.template_json_path = Path(template_json_path)
        self.templates: list[Template] = []

    def load(self) -> list[Template]:
        with self.template_json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        base_dir = self.template_json_path.parent
        self.templates = [
            Template(
                id=item["id"],
                name=item["name"],
                image_path=str((base_dir / item["image_path"]).resolve()),
                description=item.get("description", ""),
            )
            for item in data.get("templates", [])
        ]
        return self.templates

    def get(self, index: int) -> Template:
        return self.templates[index % len(self.templates)]
