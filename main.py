"""
Controlador principal del juego.
Incluye integración con sistema de guardado/carga y gestor de partidas en la UI.
"""

import sys
import pygame
import base64
import pickle
import random
from typing import Any, Dict, Optional

import config as cfg
from game_logic import Ecosystem
from game_view import GameView
from save_system import SaveManager


class GameController:
    """Controla el flujo principal del juego."""

    def __init__(self):
        self.view = GameView()
        self.ecosystem = Ecosystem()
        self.save_manager = SaveManager()

        self.running = False

        # Estado de simulación
        self.simulation_running = False
        self.simulation_paused = False
        self.next_turn_time = 0

        self.last_time = pygame.time.get_ticks()

        # Gestión de partidas
        self.current_save_id: Optional[str] = None   # partida "activa"
        self.loaded_from_save: bool = False          # se cargó desde archivo (para NO re-inicializar al comenzar)

    # ------------------------------------------------------------------
    #                    INICIALIZACIÓN
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        print("=" * 60)
        print("SIMULADOR DE ECOSISTEMA ACUÁTICO")
        print("=" * 60)

        if not self.view.initialize():
            print("✗ Error inicializando la vista")
            return False

        self.start_background_music()

        # Cargar lista de partidas existentes
        self.refresh_save_slots()

        print("✓ Juego inicializado correctamente")
        print("  Controles:")
        print("  - Gestiona partidas en el panel derecho (crear / cargar / renombrar / eliminar)")
        print("  - 'Comenzar' solo se habilita si hay una partida seleccionada")
        print("  - ESPACIO: Pausar/Reanudar")
        print("  - ESC: Salir")
        print()
        return True

    def start_background_music(self):
        try:
            pygame.mixer.music.load("assets/musica_fondo_mar.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)
        except Exception as e:
            print(f"⚠️  No se pudo cargar música de fondo: {e}")

    def refresh_save_slots(self):
        """Actualiza la lista de partidas en la vista."""
        saves = self.save_manager.list_saves()
        self.view.set_save_slots(saves, self.current_save_id)

    # ------------------------------------------------------------------
    #                      EVENTOS
    # ------------------------------------------------------------------

    def handle_events(self) -> bool:
        ev = self.view.handle_events()

        # Eventos complejos de la UI (gestor de partidas)
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
            return True

        # Eventos simples (strings)
        if ev == "quit":
            return False
        elif ev == "toggle_pause":
            self.toggle_pause()
        elif ev == "start":
            self.start_simulation()
        elif ev == "stop":
            self.stop_simulation()

        return True

    # ------------------------------------------------------------------
    #                 ACCIONES DE GESTOR DE PARTIDAS
    # ------------------------------------------------------------------

    def _random_state_to_b64(self) -> str:
        blob = pickle.dumps(random.getstate(), protocol=pickle.HIGHEST_PROTOCOL)
        return base64.b64encode(blob).decode("ascii")

    def _random_state_from_b64(self, s: str):
        try:
            blob = base64.b64decode(s.encode("ascii"))
            state = pickle.loads(blob)
            random.setstate(state)
        except Exception:
            pass

    def _build_meta_for_save(self, save_name: str) -> Dict[str, Any]:
        stats = self.ecosystem.get_statistics()
        counts = {
            "plants": stats["plants"],
            "fish": stats["fish"],
            "trout": stats["trout"],
            "sharks": stats["sharks"],
        }
        total = sum(counts.values())
        summary = (
            f"{stats['season']} | Día {stats['day']} | "
            f"{stats['time_of_day']} | P:{counts['plants']} "
            f"F:{counts['fish']} T:{counts['trout']} S:{counts['sharks']}"
        )
        return {
            "cycle": int(stats["turn"]),
            "entities_total": total,
            "counts": counts,
            "summary": summary,
            "active_config": self.view.get_configuration(),
        }

    def _build_state_for_save(self) -> Dict[str, Any]:
        controller_state = {
            "simulation_running": self.simulation_running,
            "simulation_paused": self.simulation_paused,
            "turn_progress": self.view.turn_progress,
        }
        return {
            "controller": controller_state,
            "view": {"config": self.view.get_configuration()},
            "ecosystem": self.ecosystem.to_dict(),
            "random_state_b64": self._random_state_to_b64(),
        }

    def ui_create_save(self, name: str):
        """
        Crea una nueva partida usando el estado ACTUAL del simulador.
        Puede llamarse aunque la simulación aún no haya empezado (ecosistema vacío).
        """
        meta = self._build_meta_for_save(name)
        state = self._build_state_for_save()
        save_id = self.save_manager.save(name, meta, state)

        self.current_save_id = save_id
        self.loaded_from_save = False
        self.refresh_save_slots()

        print(f"✅ Partida creada: {name} (ID: {save_id})")

    def ui_rename_save(self, save_id: str, new_name: str):
        try:
            new_id = self.save_manager.rename_save(save_id, new_name)
            if self.current_save_id == save_id:
                self.current_save_id = new_id
            self.refresh_save_slots()
            print(f"✏️  Partida renombrada a '{new_name}'")
        except Exception as e:
            print(f"❌ Error al renombrar partida: {e}")

    def ui_delete_save(self, save_id: str):
        try:
            self.save_manager.delete_save(save_id)
            if self.current_save_id == save_id:
                self.current_save_id = None
            self.refresh_save_slots()
            print("🗑️  Partida eliminada.")
        except Exception as e:
            print(f"❌ Error al eliminar partida: {e}")

    def _apply_loaded_bundle(self, bundle: Dict[str, Any]):
        """
        Aplica el contenido de un guardado al ecosistema (y al RNG).
        NO inicia la simulación: solo deja el estado listo.
        """
        state = bundle.get("state", {})

        rnd = state.get("random_state_b64")
        if isinstance(rnd, str):
            self._random_state_from_b64(rnd)

        eco_data = state.get("ecosystem")
        if isinstance(eco_data, dict):
            self.ecosystem.load_from_dict(eco_data)

        # Reseteamos estado de control: simulación detenida pero lista
        self.simulation_running = False
        self.simulation_paused = False
        self.ecosystem.set_paused(True)
        self.view.set_simulation_state(False, False)
        self.view.set_turn_progress(0.0)

    def ui_load_save(self, save_id: str):
        """
        Carga una partida desde el archivo pero NO arranca la simulación automáticamente.
        El usuario debe presionar 'Comenzar' para entrar a la simulación.
        """
        try:
            bundle = self.save_manager.load(save_id)
            self._apply_loaded_bundle(bundle)
            self.current_save_id = save_id
            self.loaded_from_save = True
            self.refresh_save_slots()
            print("📂 Partida cargada. Presiona 'Comenzar' para iniciar la simulación.")
        except Exception as e:
            print(f"❌ Error al cargar partida: {e}")

    # ------------------------------------------------------------------
    #                 CONTROL DE SIMULACIÓN
    # ------------------------------------------------------------------

    def start_simulation(self):
        """Inicia la simulación.

        Restricción: debe existir una partida seleccionada.
        Si se cargó desde un guardado, se usa ese estado.
        Si NO viene de un guardado, se inicializa desde la configuración actual.
        """
        if self.simulation_running:
            return

        if not self.current_save_id:
            print("⚠️ Debes crear o seleccionar una partida antes de comenzar.")
            return

        print("▶️  Iniciando simulación...")

        # Si NO venimos de un guardado cargado, arrancamos desde config actual
        if not self.loaded_from_save:
            config = self.view.get_configuration()
            self.ecosystem.initialize(config)

        # Marcar estado de simulación
        self.simulation_running = True
        self.simulation_paused = False
        self.ecosystem.set_paused(False)
        self.view.set_simulation_state(True, False)
        self.view.set_turn_progress(0.0)

        self.next_turn_time = pygame.time.get_ticks() + cfg.TURN_DURATION_MS

    def stop_simulation(self):
        """Detiene la simulación actual (pero NO elimina la partida)."""
        if not self.simulation_running:
            return

        print("⏹️  Deteniendo simulación...")
        self.simulation_running = False
        self.simulation_paused = False
        self.ecosystem.set_paused(True)
        self.view.set_simulation_state(False, False)

        # Mantenemos loaded_from_save como estaba; si venía de guardado, puede retomarse
        self.view.set_turn_progress(0.0)

    def toggle_pause(self):
        """Pausa o reanuda la simulación."""
        if not self.simulation_running:
            return

        self.simulation_paused = not self.simulation_paused
        self.ecosystem.set_paused(self.simulation_paused)
        self.view.set_simulation_state(True, self.simulation_paused)

        print(
            f"{'⏸️' if self.simulation_paused else '▶️'} "
            f"Simulación {'pausada' if self.simulation_paused else 'reanudada'}"
        )

    # ------------------------------------------------------------------
    #                    UPDATE LOOP
    # ------------------------------------------------------------------

    def update(self, delta_time: float):
        """Actualiza la lógica del juego."""
        if self.simulation_running and not self.simulation_paused:
            current_time = pygame.time.get_ticks()
            time_until_turn = max(0, self.next_turn_time - current_time)
            progress = 1.0 - (time_until_turn / cfg.TURN_DURATION_MS)
            self.view.set_turn_progress(progress)

            if current_time >= self.next_turn_time:
                # Aquí podrías marcar un "turno" discreto si quisieras
                self.next_turn_time = current_time + cfg.TURN_DURATION_MS

        # Actualizamos el ecosistema (movimientos, IA, etc.)
        self.ecosystem.update(delta_time)
        self.view.process_ecosystem_events(self.ecosystem.events)
        self.view.update_particles()

    # ------------------------------------------------------------------
    #                      BUCLE PRINCIPAL
    # ------------------------------------------------------------------

    def run(self):
        if not self.initialize():
            return

        self.running = True
        print("🚀 Iniciando bucle principal...")

        try:
            while self.running:
                current_time = pygame.time.get_ticks()
                delta_time = (current_time - self.last_time) / 1000.0
                self.last_time = current_time

                if not self.handle_events():
                    break

                self.update(delta_time)
                self.view.render(self.ecosystem)

        except KeyboardInterrupt:
            print("\n⏹️  Juego interrumpido por el usuario")
        except Exception as e:
            print(f"\n❌ Error en el bucle principal: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self.shutdown()

    def shutdown(self):
        print("\n🔴 Apagando juego...")
        self.view.cleanup()
        print("✓ Juego cerrado correctamente")


def main():
    game = GameController()
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
