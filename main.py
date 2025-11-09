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
    while running:
        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # IA (turnos)
        ahora = pygame.time.get_ticks()
        if ahora >= proximo_turno_ia:
            ecosistema.simular_turno_ia()
            proximo_turno_ia = ahora + TURNO_DURACION_MS

        # Movimiento continuo
        ecosistema.actualizar_movimiento_frame()

        # Render
        vista.dibujar_ecosistema(ecosistema)

        clock.tick(FPS)

    vista.cerrar()

if __name__ == "__main__":
    main()
