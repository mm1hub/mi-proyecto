"""
Sistema de visualización del juego.
Maneja la ventana, renderizado y efectos visuales.
"""

import os
import pygame
import random
import textwrap
from typing import List, Dict, Tuple, Optional, Any

import config as cfg
from game_logic import Ecosystem, Plant, Fish, Trout, Shark


class AssetLoader:
    """Cargador simple de recursos."""
    
    def __init__(self):
        self.images = {}
        self.sounds = {}
        self.fonts = {}
        
    def load_image(self, filename: str, size: Tuple[int, int] = None) -> Optional[pygame.Surface]:
        """Carga una imagen desde la carpeta assets."""
        if filename in self.images:
            return self.images[filename]
            
        path = os.path.join("assets", filename)
        if not os.path.exists(path):
            print(f"⚠️  Imagen no encontrada: {path}")
            return None
            
        try:
            image = pygame.image.load(path).convert_alpha()
            if size:
                image = pygame.transform.scale(image, size)
            self.images[filename] = image
            return image
        except Exception as e:
            print(f"✗ Error cargando imagen {filename}: {e}")
            return None
            
    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        """Carga un sonido."""
        if filename in self.sounds:
            return self.sounds[filename]
            
        path = os.path.join("assets", filename)
        if not os.path.exists(path):
            print(f"⚠️  Sonido no encontrado: {path}")
            return None
            
        try:
            sound = pygame.mixer.Sound(path)
            self.sounds[filename] = sound
            return sound
        except Exception as e:
            print(f"✗ Error cargando sonido {filename}: {e}")
            return None
            
    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        """Obtiene una fuente."""
        key = f"{size}_{bold}"
        if key not in self.fonts:
            try:
                font = pygame.font.SysFont('Arial', size, bold=bold)
                self.fonts[key] = font
            except:
                font = pygame.font.Font(None, size)
                self.fonts[key] = font
        return self.fonts[key]


class Particle:
    """Partícula visual para efectos."""
    
    def __init__(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 60  # Frames de vida
        self.speed_y = -1.5
        
    def update(self) -> bool:
        """Actualiza la partícula. Retorna True si debe eliminarse."""
        self.y += self.speed_y
        self.life -= 1
        return self.life <= 0
        
    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        """Dibuja la partícula."""
        alpha = min(255, self.life * 4)
        text_surface = font.render(self.text, True, self.color)
        text_surface.set_alpha(alpha)
        screen.blit(text_surface, (int(self.x), int(self.y)))


class GameView:
    """Ventana principal y sistema de renderizado."""
    
    def __init__(self):
        self.screen = None
        self.clock = None
        self.assets = AssetLoader()
        self.particles: List[Particle] = []
        self.effects_font = None
        
        # Estado de la simulación
        self.simulation_running = False
        self.simulation_paused = False
        
        # Panel UI
        self.panel_rect = pygame.Rect(
            cfg.SCREEN_WIDTH - cfg.PANEL_WIDTH, 0,
            cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT
        )
        
        # Botones principales
        self.setup_main_buttons()
        
        # Botones de configuración
        self.config_buttons = {}
        self.setup_config_buttons()
        
        # Configuración
        self.config = {
            'plantas': cfg.DEFAULT_POPULATION['plantas'],
            'peces': cfg.DEFAULT_POPULATION['peces'],
            'truchas': cfg.DEFAULT_POPULATION['truchas'],
            'tiburones': cfg.DEFAULT_POPULATION['tiburones']
        }
        
        # Progreso del turno
        self.turn_progress = 0.0
        
    def setup_main_buttons(self):
        """Configura los botones principales del panel."""
        padding = 20
        x = self.panel_rect.x + padding
        y = padding + 40
        width = cfg.PANEL_WIDTH - (padding * 2)
        height = 40
        
        self.btn_start = pygame.Rect(x, y, width, height)
        self.btn_pause = pygame.Rect(x, y + height + 10, width, height)
        self.btn_stop = pygame.Rect(x, y + (height + 10) * 2, width, height)
        
    def setup_config_buttons(self):
        """Configura los botones de configuración (+ y -)."""
        padding = 20
        x = self.panel_rect.x + padding
        y = self.btn_stop.bottom + 60
        
        # Configuración para cada especie
        config_items = [
            ('plantas', '🌿 Algas', y),
            ('peces', '🐟 Peces', y + 50),
            ('truchas', '🐠 Truchas', y + 100),
            ('tiburones', '🦈 Tiburones', y + 150)
        ]
        
        for key, label, y_pos in config_items:
            # Botón -
            minus_rect = pygame.Rect(x, y_pos, 30, 30)
            # Botón +
            plus_rect = pygame.Rect(x + cfg.PANEL_WIDTH - padding - 30, y_pos, 30, 30)
            # Área del valor
            value_rect = pygame.Rect(x + 40, y_pos, cfg.PANEL_WIDTH - padding * 2 - 80, 30)
            
            self.config_buttons[key] = {
                'minus': minus_rect,
                'plus': plus_rect,
                'value': value_rect,
                'label': label
            }
            
    def initialize(self) -> bool:
        """Inicializa la ventana y sistemas gráficos."""
        try:
            pygame.init()
            pygame.display.set_caption("Simulador de Ecosistema Acuático")
            
            self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
            self.clock = pygame.time.Clock()
            
            # Inicializar audio
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            
            # Cargar assets (CORREGIDO: usa .png para alga)
            self.load_assets()
            
            # Crear fuente para efectos
            self.effects_font = self.assets.get_font(18, bold=True)
            
            print("✓ Vista inicializada correctamente")
            return True
            
        except Exception as e:
            print(f"✗ Error inicializando vista: {e}")
            return False
            
    def load_assets(self):
        """Carga todos los recursos necesarios."""
        # Texturas (CORREGIDO: usa alga.png en lugar de algagif.gif)
        self.assets.load_image("pez.png", (20, 20))
        self.assets.load_image("trucha.png", (35, 35))
        self.assets.load_image("tiburon.png", (45, 45))
        self.assets.load_image("alga.png", (14, 14))  # ¡Cambiado de algagif.gif a alga.png!
        
        # Sonidos
        self.assets.load_sound("comer_planta.mp3")
        self.assets.load_sound("comer.mp3")
        self.assets.load_sound("morir.mp3")
        self.assets.load_sound("musica_fondo_mar.mp3")
        
    def handle_events(self) -> Optional[str]:
        """Procesa eventos. Retorna la acción o None."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
                
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # CORREGIDO: Solo detecta clics reales, no hover
                action = self.handle_click(event.pos)
                if action:
                    return action
                    
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                elif event.key == pygame.K_SPACE and self.simulation_running:
                    return "toggle_pause"
                    
        return None
        
    def handle_click(self, pos: Tuple[int, int]) -> Optional[str]:
        """Procesa un clic del mouse. CORREGIDO: Solo responde a clics reales."""
        # Verificar si es en el panel
        if not self.panel_rect.collidepoint(pos):
            return None
            
        # Botones de control principal (solo si están habilitados)
        if not self.simulation_running and self.btn_start.collidepoint(pos):
            return "start"
        elif self.simulation_running and self.btn_pause.collidepoint(pos):
            return "toggle_pause"
        elif self.simulation_running and self.btn_stop.collidepoint(pos):
            return "stop"
            
        # Botones de configuración (solo si la simulación NO está corriendo)
        if not self.simulation_running:
            for key, buttons in self.config_buttons.items():
                if buttons['minus'].collidepoint(pos):
                    self.config[key] = max(0, self.config[key] - 1)
                    return "config_changed"
                elif buttons['plus'].collidepoint(pos):
                    self.config[key] = min(cfg.POPULATION_LIMITS[key]["max"], self.config[key] + 1)
                    return "config_changed"
                    
        return None
        
    def update_particles(self):
        """Actualiza las partículas de efectos."""
        self.particles = [p for p in self.particles if not p.update()]
        
    def add_particle(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        """Añade una partícula de efecto."""
        self.particles.append(Particle(x, y, text, color))
        
    def process_ecosystem_events(self, events: List[Dict]):
        """Procesa eventos del ecosistema para efectos visuales."""
        for event in events:
            if event['type'] == 'eat':
                energy = int(event.get('energy', 0))
                eater = event.get('eater', '')
                color = cfg.EAT_COLOR
                
                if eater == 'pez':
                    text = f"+{energy}"
                    sound = self.assets.load_sound("comer_planta.mp3")
                else:
                    text = f"+{energy}"
                    sound = self.assets.load_sound("comer.mp3")
                    
                self.add_particle(event['position'][0], event['position'][1], text, color)
                if sound:
                    sound.play()
                    
            elif event['type'] == 'birth':
                species = event.get('species', '')
                emoji = "🐟" if species == 'pez' else "🦈" if species == 'tiburon' else "🐠"
                self.add_particle(event['position'][0], event['position'][1], f"{emoji}+1", cfg.BIRTH_COLOR)
                
            elif event['type'] == 'death':
                self.add_particle(event['position'][0], event['position'][1], "💀", cfg.DEATH_COLOR)
                sound = self.assets.load_sound("morir.mp3")
                if sound:
                    sound.play()
                    
    def draw_background(self):
        """Dibuja el fondo del juego."""
        # Gradiente de agua
        for y in range(cfg.SCREEN_HEIGHT):
            ratio = y / cfg.SCREEN_HEIGHT
            r = int(cfg.WATER_LIGHT.r * (1 - ratio) + cfg.WATER_DARK.r * ratio)
            g = int(cfg.WATER_LIGHT.g * (1 - ratio) + cfg.WATER_DARK.g * ratio)
            b = int(cfg.WATER_LIGHT.b * (1 - ratio) + cfg.WATER_DARK.b * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (cfg.GAME_AREA_WIDTH, y))
            
    def draw_entity(self, entity, image_name: str, fallback_color: pygame.Color):
        """Dibuja una entidad en pantalla. CORREGIDO: usa image_name correcto."""
        # No dibujar si está detrás del panel
        if entity.x > cfg.GAME_AREA_WIDTH - entity.width:
            return
            
        # Obtener imagen o usar fallback
        image = self.assets.load_image(image_name)
        if image:
            # Flip si mira a la izquierda
            if hasattr(entity, 'direction') and entity.direction == -1:
                image = pygame.transform.flip(image, True, False)
            self.screen.blit(image, (int(entity.x), int(entity.y)))
        else:
            # Dibujar círculo de fallback
            center = (int(entity.x + entity.width // 2), int(entity.y + entity.height // 2))
            radius = entity.width // 2
            pygame.draw.circle(self.screen, fallback_color, center, radius)
            
    def draw_ecosystem(self, ecosystem: Ecosystem):
        """Dibuja todo el ecosistema."""
        # Dibujar fondo
        self.draw_background()
        
        # Obtener todas las entidades
        all_entities = []
        all_entities.extend(ecosystem.plants)
        all_entities.extend(ecosystem.fish)
        all_entities.extend(ecosystem.trout)
        all_entities.extend(ecosystem.sharks)
        
        # Ordenar por posición Y para correcto z-ordering
        all_entities.sort(key=lambda e: e.y)
        
        # Dibujar cada entidad (CORREGIDO: usa nombres de imagen correctos)
        for entity in all_entities:
            if isinstance(entity, Plant):
                self.draw_entity(entity, "alga.png", cfg.GREEN)
            elif isinstance(entity, Fish):
                self.draw_entity(entity, "pez.png", cfg.BLUE)
            elif isinstance(entity, Trout):
                self.draw_entity(entity, "trucha.png", cfg.BROWN)
            elif isinstance(entity, Shark):
                self.draw_entity(entity, "tiburon.png", cfg.GRAY)
                
    def draw_panel(self, ecosystem: Ecosystem):
        """Dibuja el panel lateral con controles y estadísticas."""
        # Fondo del panel
        panel_surface = pygame.Surface((cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        panel_surface.fill((*cfg.PANEL_BG[:3], cfg.PANEL_BG.a if hasattr(cfg.PANEL_BG, 'a') else 230))
        self.screen.blit(panel_surface, (self.panel_rect.x, 0))
        
        # Fuentes
        title_font = self.assets.get_font(24, bold=True)
        normal_font = self.assets.get_font(18)
        small_font = self.assets.get_font(14)
        
        # Título
        title = title_font.render("Panel de Control", True, cfg.TEXT_TITLE)
        self.screen.blit(title, (self.panel_rect.x + 20, 20))
        
        # Dibujar botones principales
        self.draw_main_buttons()
        
        # Dibujar contenido según el estado
        if self.simulation_running:
            self.draw_statistics(ecosystem, small_font, normal_font)
        else:
            self.draw_configuration(small_font, normal_font)
            
    def draw_main_buttons(self):
        """Dibuja los botones principales."""
        # Botón Start (solo visible si no está corriendo)
        if not self.simulation_running:
            self.draw_button(self.btn_start, "Comenzar", cfg.BTN_START, True)
            
        # Botones Pause y Stop (solo visibles si está corriendo)
        if self.simulation_running:
            pause_text = "Pausar" if not self.simulation_paused else "Reanudar"
            pause_color = cfg.BTN_PAUSE if not self.simulation_paused else cfg.BTN_RESUME
            self.draw_button(self.btn_pause, pause_text, pause_color, True)
            self.draw_button(self.btn_stop, "Detener", cfg.BTN_STOP, True)
            
    def draw_button(self, rect: pygame.Rect, text: str, color: pygame.Color, enabled: bool):
        """Dibuja un botón con efecto hover."""
        # Color base
        btn_color = color
        
        # Efecto hover
        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)
        
        if hover and enabled:
            # Hacer el color más claro para hover
            btn_color = (min(255, color.r + 30), 
                        min(255, color.g + 30), 
                        min(255, color.b + 30))
                        
        # Si no está habilitado, hacerlo más oscuro
        if not enabled:
            btn_color = (color.r // 2, color.g // 2, color.b // 2)
                        
        # Dibujar botón
        pygame.draw.rect(self.screen, btn_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=8)
        
        # Texto
        font = self.assets.get_font(18)
        text_surface = font.render(text, True, cfg.BTN_TEXT)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)
        
    def draw_configuration(self, small_font: pygame.font.Font, normal_font: pygame.font.Font):
        """Dibuja la configuración inicial con botones + y -."""
        x = self.panel_rect.x + 20
        y = self.btn_stop.bottom + 40
        
        # Título
        config_title = normal_font.render("Configuración Inicial", True, cfg.TEXT_TITLE)
        self.screen.blit(config_title, (x, y))
        y += 50
        
        # Configuración para cada especie
        for key, buttons in self.config_buttons.items():
            # Etiqueta
            label_surface = small_font.render(buttons['label'], True, cfg.TEXT_NORMAL)
            self.screen.blit(label_surface, (x, y))
            
            # Botón -
            minus_color = cfg.BTN_MINUS if self.config[key] > 0 else (100, 100, 100)
            self.draw_button(buttons['minus'], "-", minus_color, self.config[key] > 0)
            
            # Valor
            value_surface = normal_font.render(str(self.config[key]), True, cfg.TEXT_TITLE)
            value_rect = value_surface.get_rect(center=buttons['value'].center)
            self.screen.blit(value_surface, value_rect)
            
            # Botón +
            plus_color = cfg.BTN_PLUS if self.config[key] < cfg.POPULATION_LIMITS[key]["max"] else (100, 100, 100)
            self.draw_button(buttons['plus'], "+", plus_color, self.config[key] < cfg.POPULATION_LIMITS[key]["max"])
            
            y += 50
            
    def draw_statistics(self, ecosystem: Ecosystem, small_font: pygame.font.Font, 
                       normal_font: pygame.font.Font):
        """Dibuja las estadísticas de la simulación."""
        x = self.panel_rect.x + 20
        y = self.btn_stop.bottom + 40
        
        # Título de estadísticas
        stats_title = normal_font.render("Estadísticas", True, cfg.TEXT_TITLE)
        self.screen.blit(stats_title, (x, y))
        y += 40
        
        # Obtener estadísticas
        stats = ecosystem.get_statistics()
        
        # Población
        populations = [
            ("🌿 Algas", stats['plants'], cfg.GREEN, 50),
            ("🐟 Peces", stats['fish'], cfg.BLUE, 30),
            ("🐠 Truchas", stats['trout'], cfg.BROWN, 15),
            ("🦈 Tiburones", stats['sharks'], cfg.GRAY, 10)
        ]
        
        for label, count, color, max_count in populations:
            # Texto
            text = f"{label} ({count})"
            text_surface = small_font.render(text, True, cfg.TEXT_NORMAL)
            self.screen.blit(text_surface, (x, y))
            y += 20
            
            # Barra de progreso
            progress = count / max(1, max_count)
            bar_width = cfg.PANEL_WIDTH - 40
            bar_height = 8
            
            # Fondo
            pygame.draw.rect(self.screen, cfg.BAR_BG, 
                           (x, y, bar_width, bar_height), border_radius=4)
            
            # Progreso
            if progress > 0:
                fill_width = int(bar_width * progress)
                pygame.draw.rect(self.screen, color, 
                               (x, y, fill_width, bar_height), border_radius=4)
                
            y += 25
            
        # Información de tiempo
        y += 10
        time_text = f"Día {stats['day']} · {stats['time_of_day'].capitalize()}"
        time_surface = small_font.render(time_text, True, cfg.TEXT_NORMAL)
        self.screen.blit(time_surface, (x, y))
        y += 20
        
        # Barra de progreso del día
        day_bar_width = cfg.PANEL_WIDTH - 40
        pygame.draw.rect(self.screen, cfg.BAR_BG, (x, y, day_bar_width, 6), border_radius=3)
        if stats['day_progress'] > 0:
            fill = int(day_bar_width * stats['day_progress'])
            pygame.draw.rect(self.screen, cfg.BAR_PROGRESS, (x, y, fill, 6), border_radius=3)
        y += 15
        
        # Estación
        season_text = f"Estación: {stats['season']}"
        season_surface = small_font.render(season_text, True, cfg.TEXT_TITLE)
        self.screen.blit(season_surface, (x, y))
        y += 20
        
        # Barra de progreso del turno
        y += 10
        turn_text = small_font.render("Siguiente turno IA:", True, cfg.TEXT_NORMAL)
        self.screen.blit(turn_text, (x, y))
        y += 20
        
        turn_bar_width = cfg.PANEL_WIDTH - 40
        pygame.draw.rect(self.screen, cfg.BAR_BG, (x, y, turn_bar_width, 8), border_radius=4)
        if self.turn_progress > 0:
            fill = int(turn_bar_width * self.turn_progress)
            pygame.draw.rect(self.screen, cfg.BAR_PROGRESS, (x, y, fill, 8), border_radius=4)
            
    def draw_particles(self):
        """Dibuja las partículas de efectos."""
        for particle in self.particles:
            particle.draw(self.screen, self.effects_font)
            
    def draw_pause_overlay(self):
        """Dibuja el overlay de pausa."""
        if not self.simulation_paused:
            return
            
        # Superficie semi-transparente
        overlay = pygame.Surface((cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        
        # Texto de pausa
        font = self.assets.get_font(72, bold=True)
        text = font.render("PAUSA", True, cfg.WHITE)
        text_rect = text.get_rect(center=(cfg.GAME_AREA_WIDTH // 2, cfg.SCREEN_HEIGHT // 2))
        self.screen.blit(text, text_rect)
        
    def render(self, ecosystem: Ecosystem):
        """Renderiza el frame completo."""
        # Limpiar pantalla
        self.screen.fill(cfg.BLACK)
        
        # Dibujar ecosistema
        self.draw_ecosystem(ecosystem)
        
        # Dibujar partículas
        self.draw_particles()
        
        # Dibujar panel
        self.draw_panel(ecosystem)
        
        # Dibujar overlay de pausa
        self.draw_pause_overlay()
        
        # Actualizar pantalla
        pygame.display.flip()
        self.clock.tick(cfg.FPS)
        
    def set_turn_progress(self, progress: float):
        """Establece el progreso del turno para la barra UI."""
        self.turn_progress = max(0.0, min(1.0, progress))
        
    def set_simulation_state(self, running: bool, paused: bool):
        """Establece el estado de la simulación."""
        self.simulation_running = running
        self.simulation_paused = paused
        
    def get_configuration(self) -> Dict[str, int]:
        """Obtiene la configuración actual."""
        return self.config.copy()
        
    def cleanup(self):
        """Limpia los recursos."""
        pygame.mixer.quit()
        pygame.quit()