# save_system.py
import os
import json
import re
from datetime import datetime
from typing import Any, Dict, List


class SaveManager:
    """
    Gestor de archivos de guardado.

    - Cada partida es un archivo JSON en `saves/`.
    - Formato:
        {
          "version": 1,
          "meta": {...},
          "state": {...}
        }
    """

    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)

    # ------------------- helpers internos -------------------

    def _safe_slug(self, name: str) -> str:
        name = name.strip()
        name = re.sub(r"\s+", "_", name)
        name = re.sub(r"[^a-zA-Z0-9_\-áéíóúÁÉÍÓÚñÑ]", "", name)
        return name[:40] or "save"

    def _make_save_id(self, name: str) -> str:
        ts = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        slug = self._safe_slug(name)
        return f"{ts}_{slug}"

    def _path_for_id(self, save_id: str) -> str:
        return os.path.join(self.save_dir, f"{save_id}.json")

    # ------------------- API principal -------------------

    def save(self, save_name: str, meta: Dict[str, Any], state: Dict[str, Any]) -> str:
        """Crea un nuevo archivo de guardado. Retorna save_id."""
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
        """Lista guardados con metadatos (ordenados por fecha desc)."""
        items: List[Dict[str, Any]] = []
        for filename in os.listdir(self.save_dir):
            if not filename.endswith(".json"):
                continue
            path = os.path.join(self.save_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                meta = data.get("meta", {})
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

        items.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return items

    def load(self, save_id: str) -> Dict[str, Any]:
        """Carga el contenido completo (meta + state)."""
        path = self._path_for_id(save_id)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def rename_save(self, save_id: str, new_name: str) -> str:
        """
        Renombra una partida:
        - Cambia meta.save_name
        - Cambia save_id + nombre del archivo.
        Retorna nuevo save_id.
        """
        old_path = self._path_for_id(save_id)
        if not os.path.exists(old_path):
            raise FileNotFoundError(f"No existe guardado con id {save_id}")

        with open(old_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("meta", {})
        meta["save_name"] = new_name

        new_id = self._make_save_id(new_name)
        meta["save_id"] = new_id
        data["meta"] = meta

        new_path = self._path_for_id(new_id)
        with open(new_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if os.path.exists(old_path) and old_path != new_path:
            os.remove(old_path)

        return new_id

    def delete_save(self, save_id: str) -> None:
        """Elimina definitivamente una partida (archivo .json)."""
        path = self._path_for_id(save_id)
        if os.path.exists(path):
            os.remove(path)

    # ------------------- sobrescribir guardado actual -------------------

    def overwrite(self, save_id: str, meta_updates: Dict[str, Any], state: Dict[str, Any]) -> None:
        """
        Sobrescribe el MISMO archivo (misma partida / mismo save_id).
        No cambia el formato del guardado: solo re-escribe el JSON existente.
        """
        path = self._path_for_id(save_id)
        if not os.path.exists(path):
            raise FileNotFoundError(f"No existe guardado con id {save_id}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", 1)
        meta = data.get("meta", {})
        meta["save_id"] = save_id
        meta["save_name"] = meta.get("save_name", meta_updates.get("save_name", save_id))
        meta["saved_at"] = datetime.now().astimezone().isoformat(timespec="seconds")

        for k, v in meta_updates.items():
            if k not in ("save_id", "saved_at"):
                meta[k] = v

        payload = {"version": version, "meta": meta, "state": state}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
