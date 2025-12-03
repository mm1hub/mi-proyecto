"""
Controlador principal del juego.
Versión simplificada pero funcional.
"""

import pygame
import sys
from typing import Optional

import config as cfg
from game_logic import Ecosystem
from game_view import GameView


class GameController:
    """Controla el flujo principal del juego."""
    
    def __init__(self):
        self.view = GameView()
        self.ecosystem = Ecosystem()
        self.running = False
        
        # Estado del juego
        self.simulation_running = False
        self.simulation_paused = False
        self.next_turn_time = 0
        
        # Temporizadores
        self.clock = pygame.time.Clock()
        self.last_time = pygame.time.get_ticks()
        
    def initialize(self) -> bool:
        """Inicializa todos los sistemas."""
        print("=" * 60)
        print("SIMULADOR DE ECOSISTEMA ACUÁTICO")
        print("=" * 60)
        
        # Inicializar vista
        if not self.view.initialize():
            print("✗ Error inicializando la vista")
            return False
            
        # CORREGIDO: NO inicializamos el ecosistema al inicio
        # Solo creamos un ecosistema vacío
        # El ecosistema se inicializará cuando se presione "Comenzar"
        
        # Iniciar música de fondo
        self.start_background_music()
        
        print("✓ Juego inicializado correctamente")
        print("  Controles:")
        print("  - Usa los botones + y - para configurar las poblaciones iniciales")
        print("  - Click en 'Comenzar' para iniciar la simulación")
        print("  - Click en 'Pausar/Reanudar' para controlar la simulación")
        print("  - Click en 'Detener' para terminar la simulación")
        print("  - ESPACIO para pausar/reanudar")
        print("  - ESC para salir")
        print()
        
        return True
        
    def start_background_music(self):
        """Inicia la música de fondo."""
        try:
            pygame.mixer.music.load("assets/musica_fondo_mar.mp3")
            pygame.mixer.music.set_volume(0.3)
            pygame.mixer.music.play(-1)  # Loop infinito
        except Exception as e:
            print(f"⚠️  No se pudo cargar música de fondo: {e}")
            
    def handle_events(self) -> bool:
        """Procesa eventos. Retorna False si se debe cerrar el juego."""
        # Procesar eventos de Pygame
        event_result = self.view.handle_events()
        
        if event_result == "quit":
            return False
        elif event_result == "toggle_pause":
            self.toggle_pause()
        elif event_result == "start":
            self.start_simulation()
        elif event_result == "stop":
            self.stop_simulation()
        # "config_changed" no requiere acción del controlador
            
        return True
        
    def start_simulation(self):
        """Inicia una nueva simulación."""
        if self.simulation_running:
            return
            
        print("▶️  Iniciando simulación...")
        
        # Obtener configuración de la vista
        config = self.view.get_configuration()
        print(f"  Configuración: {config}")
        
        # Inicializar ecosistema con la configuración seleccionada
        self.ecosystem.initialize(config)
        
        # Actualizar estado
        self.simulation_running = True
        self.simulation_paused = False
        self.ecosystem.set_paused(False)
        
        # Reiniciar temporizador de turnos
        self.next_turn_time = pygame.time.get_ticks() + cfg.TURN_DURATION_MS
        
        # Actualizar vista
        self.view.set_simulation_state(True, False)
        
    def stop_simulation(self):
        """Detiene la simulación actual."""
        if not self.simulation_running:
            return
            
        print("⏹️  Deteniendo simulación...")
        
        # Actualizar estado
        self.simulation_running = False
        self.simulation_paused = False
        
        # Actualizar vista
        self.view.set_simulation_state(False, False)
        
    def toggle_pause(self):
        """Alterna entre pausa y reanudación."""
        if not self.simulation_running:
            return
            
        self.simulation_paused = not self.simulation_paused
        self.ecosystem.set_paused(self.simulation_paused)
        
        # Actualizar vista
        self.view.set_simulation_state(True, self.simulation_paused)
        
        print(f"{'⏸️ ' if self.simulation_paused else '▶️ '} Simulación {'pausada' if self.simulation_paused else 'reanudada'}")
        
    def update(self, delta_time: float):
        """Actualiza la lógica del juego."""
        # Solo actualizar si la simulación está corriendo y no está pausada
        if self.simulation_running and not self.simulation_paused:
            # Actualizar progreso del turno para la UI
            current_time = pygame.time.get_ticks()
            time_until_turn = max(0, self.next_turn_time - current_time)
            progress = 1.0 - (time_until_turn / cfg.TURN_DURATION_MS)
            self.view.set_turn_progress(progress)
            
            # Ejecutar turno de IA cuando sea el momento
            if current_time >= self.next_turn_time:
                self.execute_turn()
                self.next_turn_time = current_time + cfg.TURN_DURATION_MS
                
        # Actualizar ecosistema (movimiento continuo)
        self.ecosystem.update(delta_time)
        
        # Procesar eventos del ecosistema para efectos visuales
        self.view.process_ecosystem_events(self.ecosystem.events)
        
        # Actualizar partículas
        self.view.update_particles()
        
    def execute_turn(self):
        """Ejecuta un turno completo de IA."""
        # El ecosistema ya maneja la IA en su update
        # Este método marca el momento discreto del turno
        pass
        
    def run(self):
        """Bucle principal del juego."""
        if not self.initialize():
            return
            
        self.running = True
        print("🚀 Iniciando bucle principal...")
        
        try:
            while self.running:
                # Calcular delta time
                current_time = pygame.time.get_ticks()
                delta_time = (current_time - self.last_time) / 1000.0  # En segundos
                self.last_time = current_time
                
                # Procesar eventos
                if not self.handle_events():
                    break
                    
                # Actualizar lógica
                self.update(delta_time)
                
                # Renderizar
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
        """Cierra todos los sistemas."""
        print("\n🔴 Apagando juego...")
        self.view.cleanup()
        print("✓ Juego cerrado correctamente")


def main():
    """Punto de entrada del programa."""
    game = GameController()
    game.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())