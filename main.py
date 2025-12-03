"""
Controlador principal del juego.
ARQUITECTURA CORREGIDA: Capas Estrictas.
Flow: Vista <-> Controlador -> (Lógica + Persistencia)
"""

import sys
import pygame
import base64
import pickle
import random
from typing import Any, Dict, Optional, List
import shutil
import os

import config as cfg
from game_logic import Ecosystem
from game_view import GameView, SaveSlotViewModel
from save_system import SaveManager


class GameController:
    def __init__(self):
        # Inyección de dependencias
        self.view = GameView()
        self.ecosystem = Ecosystem()
        self.save_manager = SaveManager()

        self.running = False
        
        # Estado de la Simulación
        self.simulation_running = False
        self.simulation_paused = False
        
        # Estado del Loop
        self.next_turn_time = 0
        self.last_time = pygame.time.get_ticks()

        # Estado de Sesión
        self.current_save_id: Optional[str] = None
        self.current_save_name: str = ""
        self.loaded_from_save: bool = False

        # Autoguardado
        self.auto_save_enabled: bool = False
        self.auto_save_interval_days: int = 30
        self._last_auto_saved_day: Optional[int] = None

    # ---------------- INIT ----------------

    def initialize(self) -> bool:
        print("=" * 60)
        print("SIMULADOR DE ECOSISTEMA ACUÁTICO - ARQUITECTURA EN CAPAS")
        print("=" * 60)

        if not self.view.initialize():
            return False

        self.start_background_music()
        self.refresh_ui_save_slots()
        return True

    def start_background_music(self):
        try:
            pygame.mixer.music.load("assets/musica_fondo_mar.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    # ---------------- CAPA DE ADAPTACIÓN (Persistencia -> Vista) ----------------

    def refresh_ui_save_slots(self):
        """
        Obtiene datos de Persistencia, los transforma a ViewModels
        y los envía a la Vista.
        """
        raw_saves = self.save_manager.list_saves()
        
        view_slots: List[SaveSlotViewModel] = []
        for s in raw_saves:
            slot = SaveSlotViewModel(
                id=s.get("save_id", "unknown"),
                name=s.get("save_name", "Sin Nombre"),
                display_info=s.get("summary", "")
            )
            view_slots.append(slot)

        self.view.update_save_slots(view_slots, self.current_save_id)

        if self.current_save_id:
            found = next((s for s in view_slots if s.id == self.current_save_id), None)
            self.current_save_name = found.name if found else ""
            self.view.set_active_save_name(self.current_save_name)
        else:
            self.current_save_name = ""
            self.view.set_active_save_name("")

    # ---------------- GESTIÓN DE EVENTOS (Vista -> Controlador) ----------------

    def handle_events(self) -> bool:
        ev = self.view.handle_events()

        if not ev:
            return True

        # Comandos simples (Strings)
        if isinstance(ev, str):
            if ev == "quit": return False
            if ev == "toggle_pause": self.toggle_pause()
            if ev == "start": self.start_simulation()
            if ev == "stop": self.stop_simulation()
            return True

        # Comandos con Datos (Dicts)
        t = ev.get("type")

        if t == "save_create":
            self.action_create_save(ev.get("name", ""))
        
        elif t == "save_select":
            self.current_save_id = ev.get("save_id")
            self.loaded_from_save = False
            self.refresh_ui_save_slots()
        
        elif t == "save_rename":
            self.action_rename_save(ev.get("save_id"), ev.get("new_name"))

        elif t == "save_delete":
            self.action_delete_save(ev.get("save_id"))

        elif t == "save_load":
            self.action_load_save(ev.get("save_id"))

        elif t == "save_manual":
            self.action_manual_overwrite(ev.get("save_id"))

        elif t == "auto_save_toggle":
            self.action_toggle_autosave(ev.get("enabled", False))

        elif t == "auto_save_update_interval":
            self.auto_save_interval_days = int(ev.get("days", 30))

        return True

    # ---------------- CONTROL DE SIMULACIÓN (Métodos recuperados) ----------------

    def start_simulation(self):
        if self.simulation_running:
            return
        if not self.current_save_id:
            print("⚠️ Debes crear o seleccionar una partida antes de comenzar.")
            return

        print("▶️ Iniciando simulación...")

        # Si NO venimos de cargar un save, inicializamos desde cero con la config de la vista
        if not self.loaded_from_save:
            config = self.view.get_configuration()
            self.ecosystem.initialize(config) # Controlador -> Lógica

        # Actualizar estado del Controlador
        self.simulation_running = True
        self.simulation_paused = False
        
        # Actualizar estado de la Lógica
        self.ecosystem.set_paused(False)
        
        # Actualizar estado de la Vista
        self.view.set_simulation_state(True, False)
        self.view.set_turn_progress(0.0)
        self.view.set_active_save_name(self.current_save_name)

        # Reset referencia autoguardado
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

    # ---------------- LÓGICA DE ORQUESTACIÓN (Controlador -> Persistencia) ----------------

    def _collect_game_data(self) -> Dict[str, Any]:
        """Recopila datos para guardar."""
        stats = self.ecosystem.get_statistics()
        
        counts = {k: stats[k] for k in ["plants", "fish", "trout", "sharks"]}
        summary_text = (
            f"{stats['season']} | Día {stats['day']} | {stats['time_of_day']} | "
            f"P:{counts['plants']} F:{counts['fish']} T:{counts['trout']} S:{counts['sharks']}"
        )

        meta = {
            "cycle": int(stats["turn"]),
            "entities_total": sum(counts.values()),
            "counts": counts,
            "summary": summary_text,
            "active_config": self.view.get_configuration(),
        }

        state = {
            "controller": {
                "simulation_running": self.simulation_running,
                "simulation_paused": self.simulation_paused,
            },
            "view": {"config": self.view.get_configuration()},
            "ecosystem": self.ecosystem.to_dict(),
            "random_state_b64": self._serialize_random(),
        }
        
        return {"meta": meta, "state": state}

    def action_create_save(self, name: str):
        if not name: return
        data = self._collect_game_data()
        save_id = self.save_manager.save(name, data["meta"], data["state"])
        
        self.current_save_id = save_id
        self.loaded_from_save = False
        self.refresh_ui_save_slots()
        print(f"✅ Partida creada: {name}")

    def action_rename_save(self, save_id: str, new_name: str):
        if not save_id or not new_name: return
        try:
            new_id = self.save_manager.rename_save(save_id, new_name)
            if self.current_save_id == save_id:
                self.current_save_id = new_id
            self.refresh_ui_save_slots()
        except Exception as e:
            print(f"❌ Error rename: {e}")

    def action_delete_save(self, save_id: str):
        if not save_id: return
        self.save_manager.delete_save(save_id)
        if self.current_save_id == save_id:
            self.current_save_id = None
            self.current_save_name = ""
        self.refresh_ui_save_slots()

    def action_load_save(self, save_id: str):
        if not save_id: return
        try:
            bundle = self.save_manager.load(save_id)
            self._apply_loaded_state(bundle)
            
            self.current_save_id = save_id
            self.loaded_from_save = True
            self.refresh_ui_save_slots()
            
            if self.auto_save_enabled:
                self._last_auto_saved_day = self.ecosystem.get_statistics().get("day", 0)

            print("📂 Partida cargada exitosamente.")
        except Exception as e:
            print(f"❌ Error carga: {e}")

    def action_manual_overwrite(self, save_id: str):
        data = self._collect_game_data()
        self.save_manager.overwrite(save_id, data["meta"], data["state"])
        self.refresh_ui_save_slots()
        print("💾 Guardado manual completado.")

    def action_toggle_autosave(self, enabled: bool):
        self.auto_save_enabled = enabled
        if enabled:
            self._last_auto_saved_day = self.ecosystem.get_statistics().get("day", 0)
            print(f"🔁 Autoguardado ON.")
        else:
            self._last_auto_saved_day = None
            print("⏸️ Autoguardado OFF.")

    # ---------------- HELPERS INTERNOS ----------------

    def _serialize_random(self) -> str:
        blob = pickle.dumps(random.getstate(), protocol=pickle.HIGHEST_PROTOCOL)
        return base64.b64encode(blob).decode("ascii")

    def _apply_loaded_state(self, bundle: Dict[str, Any]):
        state = bundle.get("state", {})
        
        # Restaurar Random
        rnd = state.get("random_state_b64")
        if isinstance(rnd, str):
            try:
                blob = base64.b64decode(rnd.encode("ascii"))
                random.setstate(pickle.loads(blob))
            except: pass

        # Restaurar Ecosistema
        eco_data = state.get("ecosystem", {})
        self.ecosystem.load_from_dict(eco_data)

        # Restaurar Estado
        self.simulation_running = False
        self.simulation_paused = False
        self.ecosystem.set_paused(True)
        self.view.set_simulation_state(False, False)
        self.view.set_turn_progress(0.0)

    def _check_autosave(self):
        if not (self.auto_save_enabled and self.simulation_running and not self.simulation_paused and self.current_save_id):
            return

        current_day = self.ecosystem.get_statistics().get("day", 0)
        if self._last_auto_saved_day is None:
            self._last_auto_saved_day = current_day
            return

        if current_day - self._last_auto_saved_day >= self.auto_save_interval_days:
            self.action_manual_overwrite(self.current_save_id)
            self._last_auto_saved_day = current_day
            self.view.set_auto_save_feedback(f"Autoguardado - Día {current_day}")

    # ---------------- LOOP PRINCIPAL ----------------

    def update(self, delta_time: float):
        if self.simulation_running and not self.simulation_paused:
            now = pygame.time.get_ticks()
            time_until = max(0, self.next_turn_time - now)
            progress = 1.0 - (time_until / cfg.TURN_DURATION_MS)
            self.view.set_turn_progress(progress)
            
            if now >= self.next_turn_time:
                self.next_turn_time = now + cfg.TURN_DURATION_MS

        self.ecosystem.update(delta_time)
        self.view.process_ecosystem_events(self.ecosystem.events)
        self.view.update_particles(delta_time)
        
        self._check_autosave()

    def run(self):
        if not self.initialize(): return
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
        finally:
            self.shutdown()

    def shutdown(self):
        if os.path.exists("__pycache__"):
            try: shutil.rmtree("__pycache__")
            except: pass
        self.view.cleanup()


def main():
    game = GameController()
    game.run()

if __name__ == "__main__":
    sys.exit(main())