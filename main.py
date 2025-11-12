"""Archivo principal que sincroniza la logica del ecosistema con la interfaz."""

# Empezamos con los imports. Noten la clara separación de responsabilidades:
import pygame  # El motor gráfico, nuestro "lienzo" y gestor de eventos.

# Aquí importamos nuestro 'Modelo' (Ecosistema) y las constantes del dominio.
from logic import Ecosistema, WIDTH, HEIGHT, FPS, TURNO_DURACION_MS
# Y aquí importamos nuestra 'Vista'. El 'Modelo' y la 'Vista' no se conocen.
from view import Vista


def main():
    """Configura Pygame, crea la vista y orquesta la simulacion cuadro a cuadro."""
    
    # Sección 1: Inicialización. Creamos las dos instancias principales.
    
    # Creamos el Modelo. Este objeto contiene el ESTADO de la simulación.
    ecosistema = Ecosistema()

    # Se parte de una configuracion inicial estandar de plantas y animales.
    # Dejamos que el propio modelo se configure con un estado por defecto.
    ecosistema.poblar_inicial()

    # Creamos la Vista. Este objeto sabe cómo DIBUJAR el estado.
    vista = Vista(WIDTH, HEIGHT)
    
    # La Vista maneja periféricos como el audio, desacoplando esa lógica del 'main'.
    # Se arranca musica ambiental para dar sensacion de continuidad.
    vista.iniciar_musica_fondo()

    # El 'clock' es el metrónomo de Pygame. Nos garantizará los FPS.
    clock = pygame.time.Clock()
    
    # Punto clave de la arquitectura: separamos el tiempo de LÓGICA del tiempo de RENDER.
    # Los turnos de IA se disparan cada TURNO_DURACION_MS milisegundos.
    # Usaremos 'proximo_turno_ia' como un despertador para el 'cerebro' del ecosistema.
    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS

    # Sección 2: Gestión de Estado.
    # Necesitamos una pequeña máquina de estados para controlar la aplicación.
    running = True        # Control del bucle principal (la ventana).
    sim_running = False   # Control de la simulación (activa vs. menú).
    sim_paused = False    # Control de la pausa.

    # Este es el 'Game Loop'. Todo lo que sigue se ejecuta 60 veces por segundo.
    while running:
        # --------------------------------------------
        # 1) Bucle de eventos del sistema y la UI.
        # Lo primero: 'escuchar' al usuario.
        # --------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # El usuario cerro la ventana: salir del loop principal.
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Aquí delegamos el clic a la Vista. La Vista nos dirá *qué* se pulsó.
                # Usamos 'getattr' por flexibilidad (permite 'handle_click' o 'hit_button').
                accion = getattr(vista, "handle_click", vista.hit_button)(event.pos)
                
                # Y ahora, el Controlador (aquí) decide *qué hacer* con esa acción.
                if accion == "start":
                    # Al pulsar Start se permite reconfigurar el ecosistema.
                    # Le pedimos a la Vista la configuración de la UI.
                    cfg = getattr(vista, "get_config_counts", lambda: None)()
                    
                    # Resetear la simulación es simple: creamos un *nuevo* modelo.
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
                    
                    # Activamos las banderas de estado y reseteamos el 'despertador' de la IA.
                    sim_running = True
                    sim_paused = False
                    proximo_turno_ia = pygame.time.get_ticks() + TURNO_DURACION_MS
                    vista.reproducir_sonido("start")
                
                elif accion == "pause" and sim_running:
                    # Pausar es solo un 'toggle' de bandera. No afecta al modelo.
                    sim_paused = not sim_paused
                    vista.reproducir_sonido("pause" if sim_paused else "resume")
                
                elif accion == "stop" and sim_running:
                    # Stop nos devuelve al 'menú'. Destruimos el modelo...
                    ecosistema = Ecosistema()
                    # ...y reseteamos las banderas de estado.
                    sim_running = False
                    sim_paused = False
                    vista.reproducir_sonido("stop")

        # Informamos a la Vista del estado actual (para que dibuje 'PAUSA', por ej.)
        vista.set_estado_simulacion(sim_running, sim_paused)

        # --------------------------------------------
        # 2) Turno de IA (logica discreta).
        # Esta es la sección más importante de la arquitectura.
        # --------------------------------------------
        ahora = pygame.time.get_ticks()
        # El 'cerebro' SÓLO se ejecuta si la simulación está activa y si ha llegado la hora.
        if sim_running and not sim_paused and (ahora >= proximo_turno_ia):
            # Le decimos al Modelo: 'Ejecuta tus reglas' (comer, huir, reproducirse).
            ecosistema.simular_turno_ia()
            # Y programamos el siguiente turno.
            proximo_turno_ia = ahora + TURNO_DURACION_MS

        # --------------------------------------------
        # 3) Movimiento continuo (interpolado frame a frame).
        # Si la IA decide el movimiento en el Turno 2 (cada segundo), ¿por qué se ve fluido?
        # Por esto: La IA decide el *destino*. Esta función mueve el sprite *un poco*
        # hacia ese destino en CADA frame. Es una interpolación.
        # --------------------------------------------
        if sim_running and not sim_paused:
            ecosistema.actualizar_movimiento_frame()

        # --------------------------------------------
        # 4) Calculo de progreso del siguiente turno.
        # Esta sección es puramente 'pegamento' para la UI.
        # --------------------------------------------
        if sim_running and not sim_paused:
            restante = max(0, proximo_turno_ia - ahora)
            # Calculamos un valor de 0 a 1 para la barra de progreso.
            prog = 1.0 - min(1.0, restante / float(TURNO_DURACION_MS))
        else:
            prog = 0.0
        # Y enviamos esa estadística a la Vista.
        vista.update_stats(prog)

        # --------------------------------------------
        # 5) Render final de escena y panel lateral.
        # Al final del bucle, tras actualizar la lógica, le decimos a la Vista: 'Dibuja'.
        # --------------------------------------------
        # Le pasamos el Modelo completo. La Vista sabe cómo leerlo y dibujarlo.
        vista.dibujar_ecosistema(ecosistema)

        # Aquí el 'clock' detiene la ejecución el tiempo necesario para
        # mantener nuestros 60 FPS constantes.
        clock.tick(FPS)

    # Si salimos del 'while running', limpiamos los recursos (ej. música).
    vista.cerrar()


# Y el punto de entrada estándar. Aquí es donde todo comienza.
if __name__ == "__main__":
    main()