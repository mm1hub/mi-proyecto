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
    vista.iniciar_musica_fondo()
    clock = pygame.time.Clock()
    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS
    turnos_ejecutados = 0

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
                    vista.reproducir_sonido('start')
                elif accion == 'pause' and sim_running:
                    sim_paused = not sim_paused
                    vista.reproducir_sonido('pause' if sim_paused else 'resume')
                elif accion == 'stop' and sim_running:
                    # Reinicia a un ecosistema vacío; podrás reconfigurar y comenzar de nuevo
                    ecosistema = Ecosistema()
                    sim_running = False
                    sim_paused = False
                    vista.reproducir_sonido('stop')

        # Pasar estado a la vista
        vista.set_estado_simulacion(sim_running, sim_paused)

        # IA (turnos)
        ahora = pygame.time.get_ticks()
        if sim_running and not sim_paused and (ahora >= proximo_turno_ia):
            ecosistema.simular_turno_ia()
            proximo_turno_ia = ahora + TURNO_DURACION_MS
            turnos_ejecutados += 1

        # Movimiento continuo
        if sim_running and not sim_paused:
            ecosistema.actualizar_movimiento_frame()

        # Stats de turno (progreso hacia el siguiente turno)
        if sim_running and not sim_paused:
            # progreso 0..1 del tiempo entre turnos
            restante = max(0, proximo_turno_ia - ahora)
            prog = 1.0 - min(1.0, restante / float(TURNO_DURACION_MS))
        else:
            prog = 0.0

        # Probabilidad de supervivencia (especie top)
        try:
            top, scores = ecosistema.calcular_prob_supervivencia()
        except Exception:
            top, scores = None, None

        # Actualizar UI con estadisticas (1 turno ~= 1 minuto sim)
        vista.update_stats(prog, turnos_ejecutados, top, scores)

        # Render
        vista.dibujar_ecosistema(ecosistema)

        clock.tick(FPS)

    vista.cerrar()

if __name__ == "__main__":
    main()
