"""
Controlador principal del juego.
Incluye sistema completo de guardado/carga (JSON) con metadatos.
"""

import pygame
import sys
import base64
import pickle
import random
from typing import Any, Dict, Optional

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

    def initialize(self) -> bool:
        print("=" * 60)
        print("SIMULADOR DE ECOSISTEMA ACUÁTICO")
        print("=" * 60)

        if not self.view.initialize():
            print("✗ Error inicializando la vista")
            return False

        self.start_background_music()

        print("✓ Juego inicializado correctamente")
        print("  Controles:")
        print("  - Botones panel: Comenzar / Pausar / Detener")
        print("  - ESPACIO: Pausar/Reanudar")
        print("  - F5: Guardar partida")
        print("  - F9: Cargar partida")
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

    # =========================
    #     EVENTOS Y UI
    # =========================
    def handle_events(self) -> bool:
        ev = self.view.handle_events()

        if ev == "quit":
            return False
        if ev == "toggle_pause":
            self.toggle_pause()
        elif ev == "start":
            self.start_simulation()
        elif ev == "stop":
            self.stop_simulation()
        elif ev == "save":
            self.save_flow()
        elif ev == "load":
            self.load_flow()

        return True

    def start_simulation(self):
        if self.simulation_running:
            return

        print("▶️  Iniciando simulación...")
        config = self.view.get_configuration()
        print(f"  Configuración: {config}")

        self.ecosystem.initialize(config)

        self.simulation_running = True
        self.simulation_paused = False
        self.ecosystem.set_paused(False)

        self.next_turn_time = pygame.time.get_ticks() + cfg.TURN_DURATION_MS
        self.view.set_simulation_state(True, False)

    def stop_simulation(self):
        if not self.simulation_running:
            return

        print("⏹️  Deteniendo simulación...")
        self.simulation_running = False
        self.simulation_paused = False

        # importante: congelar ecosistema si se detiene
        self.ecosystem.set_paused(True)

        self.view.set_simulation_state(False, False)

    def toggle_pause(self):
        if not self.simulation_running:
            return
        self.simulation_paused = not self.simulation_paused
        self.ecosystem.set_paused(self.simulation_paused)
        self.view.set_simulation_state(True, self.simulation_paused)
        print(f"{'⏸️' if self.simulation_paused else '▶️'} Simulación {'pausada' if self.simulation_paused else 'reanudada'}")

    # =========================
    #       UPDATE LOOP
    # =========================
    def update(self, delta_time: float):
        if not self.simulation_running:
            return

        if not self.simulation_paused:
            current_time = pygame.time.get_ticks()
            time_until_turn = max(0, self.next_turn_time - current_time)
            progress = 1.0 - (time_until_turn / cfg.TURN_DURATION_MS)
            self.view.set_turn_progress(progress)

            if current_time >= self.next_turn_time:
                self.next_turn_time = current_time + cfg.TURN_DURATION_MS

        self.ecosystem.update(delta_time)
        self.view.process_ecosystem_events(self.ecosystem.events)
        self.view.update_particles()

    # =========================
    #     GUARDADO / CARGA
    # =========================
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

    def _build_meta(self, save_name: str) -> Dict[str, Any]:
        stats = self.ecosystem.get_statistics()
        counts = {
            "plants": stats["plants"],
            "fish": stats["fish"],
            "trout": stats["trout"],
            "sharks": stats["sharks"],
        }
        total = sum(counts.values())
        summary = f"{stats['season']} | Día {stats['day']} | {stats['time_of_day']} | P:{counts['plants']} F:{counts['fish']} T:{counts['trout']} S:{counts['sharks']}"

        return {
            "cycle": int(stats["turn"]),  # ciclo = turn_count (frames/actualizaciones)
            "entities_total": total,
            "counts": counts,
            "summary": summary,
            "active_config": self.view.get_configuration(),
        }

    def _build_state(self) -> Dict[str, Any]:
        controller_state = {
            "simulation_running": self.simulation_running,
            "simulation_paused": self.simulation_paused,
            "turn_progress": getattr(self.view, "turn_progress", 0.0),
        }
        return {
            "controller": controller_state,
            "view": {"config": self.view.get_configuration()},
            "ecosystem": self.ecosystem.to_dict(),
            "random_state_b64": self._random_state_to_b64(),
        }

    def save_flow(self):
        if not self.simulation_running:
            print("⚠️ No hay simulación activa para guardar.")
            return

        was_paused = self.simulation_paused
        if not was_paused:
            self.simulation_paused = True
            self.ecosystem.set_paused(True)
            self.view.set_simulation_state(True, True)

        # Nombre del guardado (manual)
        name = input("📝 Nombre del guardado: ").strip()
        if not name:
            print("⚠️ Guardado cancelado (nombre vacío).")
            if not was_paused:
                self.simulation_paused = False
                self.ecosystem.set_paused(False)
                self.view.set_simulation_state(True, False)
            return

        meta = self._build_meta(name)
        state = self._build_state()
        save_id = self.save_manager.save(name, meta, state)

        print(f"✅ Guardado creado: {name} (ID: {save_id})")

        if not was_paused:
            self.simulation_paused = False
            self.ecosystem.set_paused(False)
            self.view.set_simulation_state(True, False)

    def load_flow(self):
        saves = self.save_manager.list_saves()

        if not saves:
            print("📭 No hay partidas guardadas en /saves")
            return

        was_paused = self.simulation_paused
        if self.simulation_running and not was_paused:
            self.simulation_paused = True
            self.ecosystem.set_paused(True)
            self.view.set_simulation_state(True, True)

        print("\n📂 Partidas guardadas:")
        for i, s in enumerate(saves, start=1):
            print(f" [{i}] {s['save_name']} | {s['saved_at']} | Ciclo:{s['cycle']} | Ent:{s['entities_total']}")
            if s.get("summary"):
                print(f"     ↳ {s['summary']}")

        choice = input("\nSelecciona número para cargar (ENTER para cancelar): ").strip()
        if not choice:
            print("↩️ Carga cancelada.")
            if self.simulation_running and not was_paused:
                self.simulation_paused = False
                self.ecosystem.set_paused(False)
                self.view.set_simulation_state(True, False)
            return

        if not choice.isdigit() or not (1 <= int(choice) <= len(saves)):
            print("❌ Selección inválida.")
            if self.simulation_running and not was_paused:
                self.simulation_paused = False
                self.ecosystem.set_paused(False)
                self.view.set_simulation_state(True, False)
            return

        selected = saves[int(choice) - 1]
        print("\n⚠️ Confirmación de carga")
        print(f" - Nombre: {selected['save_name']}")
        print(f" - Fecha: {selected['saved_at']}")
        print(f" - Resumen: {selected.get('summary','')}")
        print(" - ADVERTENCIA: Se perderá el progreso actual no guardado.")

        confirm = input("¿Cargar esta partida? (s/n): ").strip().lower()
        if confirm != "s":
            print("↩️ Carga cancelada.")
            if self.simulation_running and not was_paused:
                self.simulation_paused = False
                self.ecosystem.set_paused(False)
                self.view.set_simulation_state(True, False)
            return

        bundle = self.save_manager.load(selected["save_id"])
        state = bundle.get("state", {})

        # Restaurar random para continuidad exacta
        rnd = state.get("random_state_b64")
        if isinstance(rnd, str):
            self._random_state_from_b64(rnd)

        # Restaurar ecosistema completo
        eco_data = state.get("ecosystem", {})
        if isinstance(eco_data, dict):
            self.ecosystem.load_from_dict(eco_data)

        # Restaurar estado controlador
        ctrl = state.get("controller", {})
        self.simulation_running = bool(ctrl.get("simulation_running", True))
        self.simulation_paused = bool(ctrl.get("simulation_paused", False))
        self.ecosystem.set_paused(self.simulation_paused)

        # Turn bar
        tp = float(ctrl.get("turn_progress", 0.0))
        self.view.set_turn_progress(tp)
        remaining_ms = int(max(0, min(cfg.TURN_DURATION_MS, (1.0 - tp) * cfg.TURN_DURATION_MS)))
        self.next_turn_time = pygame.time.get_ticks() + remaining_ms

        # UI
        self.view.set_simulation_state(self.simulation_running, self.simulation_paused)

        print("✅ Partida cargada correctamente.\n")

        # Si antes estaba corriendo y no estaba pausado, vuelve a ese estado solo si la partida lo indica
        # (aquí respetamos el estado guardado).

    # =========================
    #          LOOP
    # =========================
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
