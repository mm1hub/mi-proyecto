# main.py
import pygame
# Importa todo (clases y configs) desde logic.py
from logic import Ecosistema, WIDTH, HEIGHT, FPS, TURNO_DURACION_MS
from view import Vista

def main():
    ecosistema = Ecosistema()
    
    # --- CAMBIO: Llamada al método simplificado ---
    ecosistema.poblar_inicial() # Ya no necesitamos try/except para la "ñ"

    vista = Vista(WIDTH, HEIGHT)
    clock = pygame.time.Clock()
    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS

    running = True
    sim_running = False
    sim_paused = False
    while running:
        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                accion = getattr(vista, 'handle_click', vista.hit_button)(event.pos)
                if accion == 'start':
                    # Construir ecosistema con conteos personalizados
                    cfg = getattr(vista, 'get_config_counts', lambda: None)()
                    ecosistema = Ecosistema()
                    if cfg:
                        ecosistema.poblar_custom(
                            n_plantas=cfg['plantas'],
                            n_peces=cfg['peces'],
                            n_truchas=cfg['truchas'],
                            n_tiburones=cfg['tiburones'],
                        )
                    else:
                        ecosistema.poblar_inicial()
                    sim_running = True
                    sim_paused = False
                    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS
                elif accion == 'pause' and sim_running:
                    sim_paused = not sim_paused
                elif accion == 'stop' and sim_running:
                    # Reinicia a un ecosistema vacío; podrás reconfigurar y comenzar de nuevo
                    ecosistema = Ecosistema()
                    sim_running = False
                    sim_paused = False

        # Pasar estado a la vista
        vista.set_estado_simulacion(sim_running, sim_paused)

        # IA (turnos)
        ahora = pygame.time.get_ticks()
        if sim_running and not sim_paused and (ahora >= proximo_turno_ia):
            ecosistema.simular_turno_ia()
            proximo_turno_ia = ahora + TURNO_DURACION_MS

        # Movimiento continuo
        if sim_running and not sim_paused:
            ecosistema.actualizar_movimiento_frame()

        # Render
        vista.dibujar_ecosistema(ecosistema)

        clock.tick(FPS)

    vista.cerrar()

if __name__ == "__main__":
    main()
