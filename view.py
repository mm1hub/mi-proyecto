import pygame
from logic import (
    BLANCO, AZUL, VERDE, MARRON, GRIS, 
    AGUA_CLARA, AGUA_OSCURA, NEGRO_UI,
    COLOR_TEXTO_BTN, COLOR_START, COLOR_STOP, COLOR_PAUSE, COLOR_RESUME
)

class Vista:
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema Acuático")
        self.assets = self.cargar_assets()
        
        # --- MEJORA 1: Pre-renderizar el fondo de gradiente ---
        self.fondo_superficie = self._crear_fondo_estatico(width, height)
        
        try:
            self.font = pygame.font.SysFont(None, 30)
            self.font_overlay = pygame.font.SysFont(None, 100)
        except:
            print("Warning: No se pudo cargar la fuente. La UI no se mostrará.")
            self.font = None
            self.font_overlay = None

        # --- NUEVO: Estado de la simulación ---
        self.sim_running = False
        self.sim_paused = False
        
        # --- NUEVO: Definición de botones ---
        # (x, y, ancho, alto)
        self.btn_start = pygame.Rect(self.width - 450, 5, 120, 30)
        self.btn_pause = pygame.Rect(self.width - 320, 5, 120, 30)
        self.btn_stop = pygame.Rect(self.width - 190, 5, 120, 30)


    # --- MEJORA 1: Función para crear el fondo ---
    def _crear_fondo_estatico(self, width, height):
        """
        Crea una superficie con un gradiente de agua (sin arena).
        """
        fondo = pygame.Surface((width, height))
        
        # 1. Dibujar el gradiente de agua (de claro a oscuro)
        for y in range(height):
            ratio = y / height
            r = int(AGUA_CLARA[0] * (1 - ratio) + AGUA_OSCURA[0] * ratio)
            g = int(AGUA_CLARA[1] * (1 - ratio) + AGUA_OSCURA[1] * ratio)
            b = int(AGUA_CLARA[2] * (1 - ratio) + AGUA_OSCURA[2] * ratio)
            color_interpolado = (r, g, b)
            pygame.draw.line(fondo, color_interpolado, (0, y), (width, y))
        
        return fondo

    def cargar_assets(self):
        assets = {}
        try:
            # Los tamaños ahora coinciden con los de la lógica
            assets['pez'] = pygame.transform.scale(pygame.image.load('assets/pez.png').convert_alpha(), (15, 15))
            assets['trucha'] = pygame.transform.scale(pygame.image.load('assets/trucha.png').convert_alpha(), (25, 25))
            assets['tiburon'] = pygame.transform.scale(pygame.image.load('assets/tiburon.png').convert_alpha(), (30, 30))
            assets['alga'] = pygame.transform.scale(pygame.image.load('assets/alga.png').convert_alpha(), (10, 10))
            print("Assets cargados desde 'assets/'.")
        except FileNotFoundError:
            print("Advertencia: No se encontraron imágenes en 'assets/'. Se usarán círculos.")
            assets = {}
        return assets

    # --- NUEVO: Método helper para dibujar botones ---
    def _dibujar_boton(self, rect, color, texto, color_texto=COLOR_TEXTO_BTN):
        """Dibuja un rectángulo con texto centrado."""
        pygame.draw.rect(self.screen, color, rect, border_radius=5)
        if self.font:
            img_texto = self.font.render(texto, True, color_texto)
            pos_texto = img_texto.get_rect(center=rect.center)
            self.screen.blit(img_texto, pos_texto)

    # --- NUEVO: Método helper para el overlay de pausa ---
    def dibujar_overlay_pausa(self):
        """Dibuja un overlay oscuro y texto de "PAUSA"."""
        if not self.font_overlay:
            return
            
        # Superficie oscura semi-transparente
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128)) # Negro al 50% de opacidad
        self.screen.blit(overlay, (0, 0))
        
        # Texto "PAUSA"
        img_pausa = self.font_overlay.render("PAUSA", True, BLANCO)
        pos_pausa = img_pausa.get_rect(center=(self.width / 2, self.height / 2))
        self.screen.blit(img_pausa, pos_pausa)


    def dibujar_ecosistema(self, ecosistema):
        # --- MEJORA 1: Dibujar el fondo de gradiente ---
        self.screen.blit(self.fondo_superficie, (0, 0))

        # --- DIBUJO DE ENTIDADES (Sin cambios) ---
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

        # --- DIBUJO DE UI (Actualizado) ---
        self.dibujar_ui(ecosistema)
        
        # --- NUEVO: Dibujar overlay si está en pausa ---
        if self.sim_running and self.sim_paused:
            self.dibujar_overlay_pausa()

        pygame.display.flip()

    def dibujar_ui(self, ecosistema):
        if not self.font:
            return
            
        # --- MEJORA 3: Panel de UI semi-transparente ---
        panel_ui = pygame.Surface((self.width, 40), pygame.SRCALPHA)
        panel_ui.fill((240, 240, 240, 180)) # Blanco, semi-transparente
        self.screen.blit(panel_ui, (0, 0))

        # --- Estadísticas (Lado izquierdo) ---
        textos = [
            (f"Algas: {len(ecosistema.plantas)}", VERDE, 10),
            (f"Peces: {len(ecosistema.peces)}", AZUL, 130),
            (f"Truchas: {len(ecosistema.truchas)}", MARRON, 260),
            (f"Tiburones: {len(ecosistema.tiburones)}", GRIS, 420),
        ]
        
        for (texto, color, x_pos) in textos:
            img = self.font.render(texto, True, NEGRO_UI) 
            self.screen.blit(img, (x_pos, 10))
            
        # --- NUEVO: Botones de control (Lado derecho) ---
        
        # Botón Start/Comenzar
        if not self.sim_running:
            self._dibujar_boton(self.btn_start, COLOR_START, "Comenzar")
        
        # Botones Pause y Stop (solo si la simulación está corriendo)
        if self.sim_running:
            # El botón de Pausa cambia de texto y color
            if self.sim_paused:
                self._dibujar_boton(self.btn_pause, COLOR_RESUME, "Reanudar")
            else:
                self._dibujar_boton(self.btn_pause, COLOR_PAUSE, "Pausar")
                
            self._dibujar_boton(self.btn_stop, COLOR_STOP, "Detener")

    # --- NUEVO: Método requerido por main.py ---
    def set_estado_simulacion(self, sim_running, sim_paused):
        """Recibe el estado desde main.py y lo guarda."""
        self.sim_running = sim_running
        self.sim_paused = sim_paused

    # --- NUEVO: Método requerido por main.py ---
    def hit_button(self, pos):
        """Comprueba si un click (pos) ha golpeado un botón."""
        if self.btn_start.collidepoint(pos) and not self.sim_running:
            return 'start'
        if self.btn_pause.collidepoint(pos) and self.sim_running:
            return 'pause'
        if self.btn_stop.collidepoint(pos) and self.sim_running:
            return 'stop'
        return None

    def cerrar(self):
        pygame.quit()