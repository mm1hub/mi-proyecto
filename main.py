"""
Controlador principal del juego.
Incluye integración con sistema de guardado/carga + gestor de partidas UI + guardado manual.
+ Sistema de AUTOGUARDADO configurable desde la interfaz.
+ Limpieza de archivos temporales al cerrar la aplicación (elimina __pycache__).
"""

import sys
import pygame
import base64
import pickle
import random
from typing import Any, Dict, Optional
import shutil
import os

import config as cfg
from game_logic import Ecosystem
from game_view import GameView
from save_system import SaveManager


class GameController:
    def __init__(self):
        self.view = GameView()
        self.ecosystem = Ecosystem()
        self.save_manager = SaveManager()

        self.running = False

        self.simulation_running = False
        self.simulation_paused = False
        self.next_turn_time = 0
        self.last_time = pygame.time.get_ticks()

        self.current_save_id: Optional[str] = None
        self.current_save_name: str = ""   # usado para mostrar el nombre arriba izq
        self.loaded_from_save: bool = False

        # ---------------- AUTOGUARDADO ----------------
        self.auto_save_enabled: bool = False          # si el sistema está activo
        self.auto_save_interval_days: int = 30        # N días (configurable)
        self._last_auto_saved_day: Optional[int] = None  # último día en que se hizo autoguardado

    # ---------------- init ----------------

    def initialize(self) -> bool:
        print("=" * 60)
        print("SIMULADOR DE ECOSISTEMA ACUÁTICO")
        print("=" * 60)

        if not self.view.initialize():
            print("✗ Error inicializando la vista")
            return False

        self.start_background_music()
        self.refresh_save_slots()

        print("✓ Juego inicializado correctamente")
        return True

    def start_background_music(self):
        try:
            pygame.mixer.music.load("assets/musica_fondo_mar.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"⚠️  No se pudo cargar música de fondo: {e}")

    def refresh_save_slots(self):
        saves = self.save_manager.list_saves()
        self.view.set_save_slots(saves, self.current_save_id)

        # actualizar nombre desde lista
        if self.current_save_id:
            slot = next((s for s in saves if s["save_id"] == self.current_save_id), None)
            if slot:
                self.current_save_name = slot["save_name"]
                self.view.set_active_save_name(self.current_save_name)
            else:
                self.current_save_name = ""
                self.view.set_active_save_name("")

    # ---------------- eventos ----------------

    def handle_events(self) -> bool:
        ev = self.view.handle_events()

        if isinstance(ev, dict):
            t = ev.get("type")

            if t == "save_create":
                name = ev.get("name", "").strip()
                if name:
                    self.ui_create_save(name)

            elif t == "save_select":
                save_id = ev.get("save_id")
                self.current_save_id = save_id
                self.loaded_from_save = False
                self.refresh_save_slots()

            elif t == "save_rename":
                save_id = ev.get("save_id")
                new_name = ev.get("new_name", "").strip()
                if save_id and new_name:
                    self.ui_rename_save(save_id, new_name)

            elif t == "save_delete":
                save_id = ev.get("save_id")
                if save_id:
                    self.ui_delete_save(save_id)

            elif t == "save_load":
                save_id = ev.get("save_id")
                if save_id:
                    self.ui_load_save(save_id)

            elif t == "save_manual":
                save_id = ev.get("save_id")
                if save_id:
                    self.ui_manual_save_overwrite(save_id)

            # ---------- NUEVOS EVENTOS: AUTOGUARDADO ----------
            elif t == "auto_save_toggle":
                enabled = bool(ev.get("enabled", False))
                self.auto_save_enabled = enabled
                if enabled:
                    # al activar, fijamos el día actual como referencia
                    stats = self.ecosystem.get_statistics()
                    self._last_auto_saved_day = stats.get("day", 0)
                    print(f"🔁 Autoguardado activado (cada {self.auto_save_interval_days} días).")
                else:
                    # al desactivar, cortamos completamente la lógica
                    self._last_auto_saved_day = None
                    print("⏸️ Autoguardado desactivado.")

            elif t == "auto_save_update_interval":
                days = int(ev.get("days", self.auto_save_interval_days))
                days = max(1, days)
                self.auto_save_interval_days = days
                print(f"⚙️ Intervalo de autoguardado actualizado a cada {self.auto_save_interval_days} días.")

            return True

        if ev == "quit":
            return False
        if ev == "toggle_pause":
            self.toggle_pause()
        if ev == "start":
            self.start_simulation()
        if ev == "stop":
            self.stop_simulation()

        return True

    # ---------------- guardado / carga (estado) ----------------

    def _random_state_to_b64(self) -> str:
        blob = pickle.dumps(random.getstate(), protocol=pickle.HIGHEST_PROTOCOL)
        return base64.b64encode(blob).decode("ascii")

    def _random_state_from_b64(self, s: str):
        try:
            blob = base64.b64decode(s.encode("ascii"))
            random.setstate(pickle.loads(blob))
        except Exception:
            pass

    def _build_meta_for_save(self) -> Dict[str, Any]:
        stats = self.ecosystem.get_statistics()
        counts = {
            "plants": stats["plants"],
            "fish": stats["fish"],
            "trout": stats["trout"],
            "sharks": stats["sharks"],
        }
        total = sum(counts.values())
        summary = (
            f"{stats['season']} | Día {stats['day']} | {stats['time_of_day']} | "
            f"P:{counts['plants']} F:{counts['fish']} T:{counts['trout']} S:{counts['sharks']}"
        )
        return {
            "cycle": int(stats["turn"]),
            "entities_total": total,
            "counts": counts,
            "summary": summary,
            "active_config": self.view.get_configuration(),
        }

    def _build_state_for_save(self) -> Dict[str, Any]:
        return {
            "controller": {
                "simulation_running": self.simulation_running,
                "simulation_paused": self.simulation_paused,
                "turn_progress": self.view.turn_progress,
            },
            "view": {"config": self.view.get_configuration()},
            "ecosystem": self.ecosystem.to_dict(),
            "random_state_b64": self._random_state_to_b64(),
        }

    # ---------------- UI acciones partidas ----------------

    def ui_create_save(self, name: str):
        meta = self._build_meta_for_save()
        state = self._build_state_for_save()
        save_id = self.save_manager.save(name, meta, state)

        self.current_save_id = save_id
        self.loaded_from_save = False
        self.refresh_save_slots()

        print(f"✅ Partida creada: {name}")

    def ui_rename_save(self, save_id: str, new_name: str):
        try:
            new_id = self.save_manager.rename_save(save_id, new_name)
            if self.current_save_id == save_id:
                self.current_save_id = new_id
            self.refresh_save_slots()
            print(f"✏️  Partida renombrada a '{new_name}'")
        except Exception as e:
            print(f"❌ Error al renombrar: {e}")

    def ui_delete_save(self, save_id: str):
        try:
            self.save_manager.delete_save(save_id)
            if self.current_save_id == save_id:
                self.current_save_id = None
                self.current_save_name = ""
                self.view.set_active_save_name("")
            self.refresh_save_slots()
            print("🗑️  Partida eliminada.")
        except Exception as e:
            print(f"❌ Error al eliminar: {e}")

    def _apply_loaded_bundle(self, bundle: Dict[str, Any]):
        state = bundle.get("state", {})

        rnd = state.get("random_state_b64")
        if isinstance(rnd, str):
            self._random_state_from_b64(rnd)

        eco = state.get("ecosystem", {})
        if isinstance(eco, dict):
            self.ecosystem.load_from_dict(eco)

        self.simulation_running = False
        self.simulation_paused = False
        self.ecosystem.set_paused(True)
        self.view.set_simulation_state(False, False)
        self.view.set_turn_progress(0.0)

    def ui_load_save(self, save_id: str):
        try:
            bundle = self.save_manager.load(save_id)
            self._apply_loaded_bundle(bundle)

            self.current_save_id = save_id
            self.loaded_from_save = True
            self.refresh_save_slots()

            # al cargar, si el autoguardado está activo, anclamos el día actual
            if self.auto_save_enabled:
                stats = self.ecosystem.get_statistics()
                self._last_auto_saved_day = stats.get("day", 0)

            print("📂 Partida cargada. Presiona 'Comenzar' para entrar.")
        except Exception as e:
            print(f"❌ Error al cargar: {e}")

    # ---------------- guardado manual ----------------

    def ui_manual_save_overwrite(self, save_id: str):
        """
        Sobrescribe el archivo de la partida actual (misma ID) usando el sistema existente.
        """
        try:
            meta = self._build_meta_for_save()
            state = self._build_state_for_save()
            self.save_manager.overwrite(save_id, meta, state)
            self.refresh_save_slots()
            print("💾 Guardado manual realizado (sobrescrito).")
        except Exception as e:
            print(f"❌ Error guardado manual: {e}")

    # ---------------- AUTOGUARDADO (LÓGICA INTERNA) ----------------

    def _maybe_auto_save(self):
        """
        Verifica si corresponde hacer un autoguardado según:
        - Autoguardado activado
        - Simulación corriendo y no en pausa
        - Existe una partida actual (current_save_id)
        - Han pasado N días desde el último autoguardado
        """
        if not self.auto_save_enabled:
            return
        if not self.simulation_running or self.simulation_paused:
            return
        if not self.current_save_id:
            return

        stats = self.ecosystem.get_statistics()
        current_day = stats.get("day", 0)

        if self._last_auto_saved_day is None:
            self._last_auto_saved_day = current_day
            return

        if current_day - self._last_auto_saved_day >= self.auto_save_interval_days:
            try:
                meta = self._build_meta_for_save()
                state = self._build_state_for_save()
                self.save_manager.overwrite(self.current_save_id, meta, state)
                self.refresh_save_slots()
                self._last_auto_saved_day = current_day

                print(f"💾 Autoguardado automático realizado (Día {current_day}).")
                # Mensaje visual en la interfaz (no intrusivo)
                self.view.set_auto_save_feedback(f"Autoguardado automático - Día {current_day}")
            except Exception as e:
                print(f"❌ Error en autoguardado: {e}")

    # ---------------- simulación ----------------

    def start_simulation(self):
        if self.simulation_running:
            return
        if not self.current_save_id:
            print("⚠️ Debes crear o seleccionar una partida antes de comenzar.")
            return

        print("▶️ Iniciando simulación...")

        if not self.loaded_from_save:
            config = self.view.get_configuration()
            self.ecosystem.initialize(config)

        self.simulation_running = True
        self.simulation_paused = False
        self.ecosystem.set_paused(False)
        self.view.set_simulation_state(True, False)
        self.view.set_turn_progress(0.0)

        # asegurar nombre visible arriba izq
        self.view.set_active_save_name(self.current_save_name)

        # reset de referencia del autoguardado si está activo
        if self.auto_save_enabled:
            stats = self.ecosystem.get_statistics()
            self._last_auto_saved_day = stats.get("day", 0)

        self.next_turn_time = pygame.time.get_ticks() + cfg.TURN_DURATION_MS

    def stop_simulation(self):
        if not self.simulation_running:
            return
        print("⏹️ Deteniendo simulación...")
        self.simulation_running = False
        self.simulation_paused = False
        self.ecosystem.set_paused(True)
        self.view.set_simulation_state(False, False)
        self.view.set_turn_progress(0.0)

    def toggle_pause(self):
        if not self.simulation_running:
            return
        self.simulation_paused = not self.simulation_paused
        self.ecosystem.set_paused(self.simulation_paused)
        self.view.set_simulation_state(True, self.simulation_paused)

    # ---------------- loop ----------------

    def update(self, delta_time: float):
        if self.simulation_running and not self.simulation_paused:
            now = pygame.time.get_ticks()
            time_until_turn = max(0, self.next_turn_time - now)
            progress = 1.0 - (time_until_turn / cfg.TURN_DURATION_MS)
            self.view.set_turn_progress(progress)
            if now >= self.next_turn_time:
                self.next_turn_time = now + cfg.TURN_DURATION_MS

        # Actualizamos lógica del ecosistema
        self.ecosystem.update(delta_time)
        self.view.process_ecosystem_events(self.ecosystem.events)

        # Partículas + timers de UI (incluye mensaje de autoguardado)
        self.view.update_particles(delta_time)

        # Verificamos si corresponde hacer autoguardado
        self._maybe_auto_save()

    def run(self):
        if not self.initialize():
            return
        self.running = True
        try:
            while self.running:
                now = pygame.time.get_ticks()
                delta = (now - self.last_time) / 1000.0
                self.last_time = now

                if not self.handle_events():
                    break

                self.update(delta)
                self.view.render(self.ecosystem)

        except Exception as e:
            print(f"\n❌ Error en el bucle principal: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()

    def shutdown(self):
        print("\n🔴 Apagando juego...")

        # Limpiar archivos temporales: eliminar la carpeta __pycache__
        self.clean_temp_files()

        self.view.cleanup()
        print("✓ Juego cerrado correctamente")

    def clean_temp_files(self):
        """Elimina archivos temporales como __pycache__ al cerrar el juego."""
        pycache_path = "__pycache__"
        
        if os.path.exists(pycache_path):
            try:
                shutil.rmtree(pycache_path)  # Elimina la carpeta __pycache__ y todo su contenido
                print("🔄 Carpeta __pycache__ eliminada correctamente.")
            except Exception as e:
                print(f"⚠️ No se pudo eliminar __pycache__: {e}")
        else:
            print("⚠️ No se encontró la carpeta __pycache__ para eliminar.")


def main():
    game = GameController()
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
