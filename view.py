# view.py
import pygame
from logic import BLANCO, AZUL, VERDE, MARRON, GRIS

class Vista:
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema")
        self.assets = self.cargar_assets()
        # Estado de simulación y botones
        self.sim_running = False
        self.sim_paused = False
        # Botones en la barra superior
        self.btn_start = pygame.Rect(self.width - 300, 5, 90, 30)
        self.btn_pause = pygame.Rect(self.width - 200, 5, 90, 30)
        self.btn_stop = pygame.Rect(self.width - 100, 5, 90, 30)
        try:
            self.font = pygame.font.SysFont(None, 30)
        except:
            print("Warning: No se pudo cargar la fuente. La UI no se mostrará.")
            self.font = None

    def set_estado_simulacion(self, running: bool, paused: bool):
        self.sim_running = running
        self.sim_paused = paused

    def cargar_assets(self):
        assets = {}
        try:
            assets['pez'] = pygame.transform.scale(pygame.image.load('assets/pez.png').convert_alpha(), (15, 15))
            assets['trucha'] = pygame.transform.scale(pygame.image.load('assets/trucha.png').convert_alpha(), (25, 25))
            assets['tiburon'] = pygame.transform.scale(pygame.image.load('assets/tiburon.png').convert_alpha(), (30, 30))
            assets['alga'] = pygame.transform.scale(pygame.image.load('assets/alga.png').convert_alpha(), (10, 10))
            print("Assets cargados desde 'assets/'.")
        except FileNotFoundError:
            print("Advertencia: No se encontraron imágenes en 'assets/'. Se usarán círculos.")
            assets = {}
        return assets

    def dibujar_ecosistema(self, ecosistema):
        self.screen.fill(BLANCO)

        # Plantas
        for planta in ecosistema.plantas:
            if 'alga' in self.assets:
                self.screen.blit(self.assets['alga'], planta.rect)
            else:
                pygame.draw.circle(self.screen, VERDE, planta.rect.center, 5)

        # Peces
        for pez in ecosistema.peces:
            if 'pez' in self.assets:
                self.screen.blit(self.assets['pez'], pez.rect)
            else:
                pygame.draw.circle(self.screen, AZUL, pez.rect.center, 8)

        # Truchas
        for trucha in ecosistema.truchas:
            if 'trucha' in self.assets:
                self.screen.blit(self.assets['trucha'], trucha.rect)
            else:
                pygame.draw.circle(self.screen, MARRON, trucha.rect.center, 12)

        # Tiburones
        for tiburon in ecosistema.tiburones:
            if 'tiburon' in self.assets:
                self.screen.blit(self.assets['tiburon'], tiburon.rect)
            else:
                pygame.draw.circle(self.screen, GRIS, tiburon.rect.center, 15)

        self.dibujar_ui(ecosistema)
        pygame.display.flip()

    def dibujar_ui(self, ecosistema):
        if not self.font:
            return
        pygame.draw.rect(self.screen, (240, 240, 240), (0, 0, self.width, 40))
        textos = [
            (f"Algas: {len(ecosistema.plantas)}", VERDE, 10),
            (f"Peces: {len(ecosistema.peces)}", AZUL, 130),
            (f"Truchas: {len(ecosistema.truchas)}", MARRON, 260),
            (f"Tiburones: {len(ecosistema.tiburones)}", GRIS, 420),
        ]
        for (texto, color, x_pos) in textos:
            img = self.font.render(texto, True, color)
            self.screen.blit(img, (x_pos, 10))

        # Botones de control
        self._draw_button(self.btn_start, "Iniciar", activo=not self.sim_running)
        self._draw_button(self.btn_pause, "Pausar" if not self.sim_paused else "Reanudar", activo=self.sim_running)
        self._draw_button(self.btn_stop, "Detener", activo=self.sim_running)

    def _draw_button(self, rect: pygame.Rect, texto: str, activo: bool = True):
        color_bg = (200, 200, 200) if activo else (220, 220, 220)
        color_fg = (0, 0, 0) if activo else (100, 100, 100)
        pygame.draw.rect(self.screen, color_bg, rect, border_radius=6)
        pygame.draw.rect(self.screen, (150, 150, 150), rect, 2, border_radius=6)
        if self.font:
            img = self.font.render(texto, True, color_fg)
            text_rect = img.get_rect(center=rect.center)
            self.screen.blit(img, text_rect)

    def hit_button(self, pos):
        if self.btn_start.collidepoint(pos):
            return 'start'
        if self.btn_pause.collidepoint(pos):
            return 'pause'
        if self.btn_stop.collidepoint(pos):
            return 'stop'
        return None

    def cerrar(self):
        pygame.quit()
