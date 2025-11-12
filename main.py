"""Archivo principal que sincroniza la logica del ecosistema con la interfaz."""

import pygame

from logic import Ecosistema, WIDTH, HEIGHT, FPS, TURNO_DURACION_MS
from view import Vista


def main():
    """Configura Pygame, crea la vista y orquesta la simulacion cuadro a cuadro."""
    ecosistema = Ecosistema()

    # Se parte de una configuracion inicial estandar de plantas y animales.
    ecosistema.poblar_inicial()

    vista = Vista(WIDTH, HEIGHT)
    # Se arranca musica ambiental para dar sensacion de continuidad.
    vista.iniciar_musica_fondo()
    clock = pygame.time.Clock()
    # Los turnos de IA se disparan cada TURNO_DURACION_MS milisegundos.
    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS

    running = True          # Control del bucle principal de la ventana.
    sim_running = False     # Indica si la simulacion esta activa.
    sim_paused = False      # Indica si la simulacion esta pausada.
    while running:
        # --------------------------------------------
        # 1) Bucle de eventos del sistema y la UI.
        # --------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # El usuario cerro la ventana: salir del loop principal.
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # handle_click existe en la version nueva, hit_button en la antigua.
                accion = getattr(vista, "handle_click", vista.hit_button)(event.pos)
                if accion == "start":
                    # Al pulsar Start se permite reconfigurar el ecosistema.
                    cfg = getattr(vista, "get_config_counts", lambda: None)()
                    ecosistema = Ecosistema()
                    if cfg:
                        # Se puebla con los valores provistos por la UI lateral.
                        ecosistema.poblar_custom(
                            n_plantas=cfg["plantas"],
                            n_peces=cfg["peces"],
                            n_truchas=cfg["truchas"],
                            n_tiburones=cfg["tiburones"],
                        )
                    else:
                        # Fallback: usa la configuracion interna por defecto.
                        ecosistema.poblar_inicial()
                    sim_running = True
                    sim_paused = False
                    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS
                    vista.reproducir_sonido("start")
                elif accion == "pause" and sim_running:
                    sim_paused = not sim_paused
                    vista.reproducir_sonido("pause" if sim_paused else "resume")
                elif accion == "stop" and sim_running:
                    # Stop destruye el estado actual para volver a configurar.
                    ecosistema = Ecosistema()
                    sim_running = False
                    sim_paused = False
                    vista.reproducir_sonido("stop")

        # La vista necesita saber si mostrar overlays de pausa o mensajes.
        vista.set_estado_simulacion(sim_running, sim_paused)

        # --------------------------------------------
        # 2) Turno de IA (logica discreta).
        # --------------------------------------------
        ahora = pygame.time.get_ticks()
        if sim_running and not sim_paused and (ahora >= proximo_turno_ia):
            ecosistema.simular_turno_ia()
            proximo_turno_ia = ahora + TURNO_DURACION_MS

        # --------------------------------------------
        # 3) Movimiento continuo (interpolado frame a frame).
        # --------------------------------------------
        if sim_running and not sim_paused:
            ecosistema.actualizar_movimiento_frame()

        # --------------------------------------------
        # 4) Calculo de progreso del siguiente turno.
        # --------------------------------------------
        if sim_running and not sim_paused:
            restante = max(0, proximo_turno_ia - ahora)
            # prog es un valor normalizado (0 a 1) para la barra lateral.
            prog = 1.0 - min(1.0, restante / float(TURNO_DURACION_MS))
        else:
            prog = 0.0
        # Se reenvia el progreso a la vista para que actualice textos y barras.
        vista.update_stats(prog)

        # --------------------------------------------
        # 5) Render final de escena y panel lateral.
        # --------------------------------------------
        vista.dibujar_ecosistema(ecosistema)

        # clock.tick limita la ejecucion a FPS e informa delta time.
        clock.tick(FPS)

    vista.cerrar()


if __name__ == "__main__":
    main()

