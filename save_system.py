# save_system.py
import os
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


class SaveManager:
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    def _safe_slug(self, name: str) -> str:
        name = name.strip()
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^a-zA-Z0-9_\-áéíóúÁÉÍÓÚñÑ]", "", name)
        return name[:40] or "save"

    def _make_save_id(self, save_name: str) -> str:
        ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        slug = self._safe_slug(save_name)
        return f"{ts}_{slug}"

    def _path_for_id(self, save_id: str) -> str:
        return os.path.join(self.save_dir, f"{save_id}.json")

    def save(self, save_name: str, meta: Dict[str, Any], state: Dict[str, Any]) -> str:
        save_id = self._make_save_id(save_name)
        payload = {
            "version": 1,
            "meta": {
                "save_id": save_id,
                "save_name": save_name,
                "saved_at": datetime.now().astimezone().isoformat(timespec="seconds"),
                **meta,
            },
            "state": state,
        }
        path = self._path_for_id(save_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return save_id

    def list_saves(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for filename in os.listdir(self.save_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.save_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                meta = data.get("meta", {})
                # Asegurar campos mínimos
                save_id = meta.get("save_id") or filename[:-5]
                items.append(
                    {
                        "save_id": save_id,
                        "save_name": meta.get("save_name", save_id),
                        "saved_at": meta.get("saved_at", ""),
                        "cycle": meta.get("cycle", 0),
                        "entities_total": meta.get("entities_total", 0),
                        "summary": meta.get("summary", ""),
                        "counts": meta.get("counts", {}),
                        "active_config": meta.get("active_config", {}),
                    }
                )
            except Exception:
                continue

        def sort_key(x: Dict[str, Any]) -> str:
            return x.get("saved_at", "")

        items.sort(key=sort_key, reverse=True)
        return items

    def load(self, save_id: str) -> Dict[str, Any]:
        path = self._path_for_id(save_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
