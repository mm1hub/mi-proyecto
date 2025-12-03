"""
Sistema de visualización del juego.
Maneja la ventana, renderizado y efectos visuales.
"""

import os
import pygame
import random
from typing import List, Dict, Tuple, Optional, Any

import config as cfg
from game_logic import Ecosystem, Plant, Fish, Trout, Shark


class AssetLoader:
    """Cargador simple de recursos."""

    def __init__(self):
        self.images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.fonts: Dict[str, pygame.font.Font] = {}

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
                font = pygame.font.SysFont("Arial", size, bold=bold)
                self.fonts[key] = font
            except Exception:
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
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.assets = AssetLoader()
        self.particles: List[Particle] = []
        self.effects_font: Optional[pygame.font.Font] = None

        # Estado de la simulación
        self.simulation_running = False
        self.simulation_paused = False

        # Panel UI
        self.panel_rect = pygame.Rect(
            cfg.SCREEN_WIDTH - cfg.PANEL_WIDTH, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT
        )

        # Botones principales
        self.setup_main_buttons()

        # Botones de configuración poblaciones
        self.config_buttons: Dict[str, Dict[str, Any]] = {}
        self.setup_config_buttons()

        # Configuración de poblaciones
        self.config: Dict[str, int] = {
            "plantas": cfg.DEFAULT_POPULATION["plantas"],
            "peces": cfg.DEFAULT_POPULATION["peces"],
            "truchas": cfg.DEFAULT_POPULATION["truchas"],
            "tiburones": cfg.DEFAULT_POPULATION["tiburones"],
        }

        # Progreso del turno IA
        self.turn_progress = 0.0

        # --------- UI de partidas ---------
        self.save_slots: List[Dict[str, Any]] = []
        self.selected_save_id: Optional[str] = None

        self.pending_delete_id: Optional[str] = None

        # Estado del campo de texto
        self.text_input_active = False
        self.text_input_value: str = ""
        self.text_input_mode: Optional[str] = None  # "create" o "rename"
        self.text_input_target_id: Optional[str] = None

        # Rectángulos de la UI de partidas
        self.save_ui_rects: Dict[str, Any] = {
            "input": None,
            "create_btn": None,
            "load_btn": None,
            "slots": {},  # save_id -> {"row": rect, "rename": rect, "delete": rect}
        }

    # ------------------------------------------------------------------
    #    CONFIGURACIÓN INICIAL DE BOTONES
    # ------------------------------------------------------------------

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
        """Configura los botones de configuración (+ y -) de poblaciones."""
        padding = 20
        x = self.panel_rect.x + padding
        y = self.btn_stop.bottom + 220  # se deja espacio para la gestión de partidas

        config_items = [
            ("plantas", "🌿 Algas", y),
            ("peces", "🐟 Peces", y + 50),
            ("truchas", "🐠 Truchas", y + 100),
            ("tiburones", "🦈 Tiburones", y + 150),
        ]

        for key, label, y_pos in config_items:
            minus_rect = pygame.Rect(x, y_pos, 30, 30)
            plus_rect = pygame.Rect(
                x + cfg.PANEL_WIDTH - padding - 30, y_pos, 30, 30
            )
            value_rect = pygame.Rect(
                x + 40, y_pos, cfg.PANEL_WIDTH - padding * 2 - 80, 30
            )

            self.config_buttons[key] = {
                "minus": minus_rect,
                "plus": plus_rect,
                "value": value_rect,
                "label": label,
            }

    # ------------------------------------------------------------------
    #          MÉTODOS GENERALES DEL VIEW
    # ------------------------------------------------------------------

    def initialize(self) -> bool:
        """Inicializa la ventana y sistemas gráficos."""
        try:
            pygame.init()
            pygame.display.set_caption("Simulador de Ecosistema Acuático")

            self.screen = pygame.display.set_mode(
                (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT)
            )
            self.clock = pygame.time.Clock()

            # Inicializar audio
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

            # Cargar assets
            self.load_assets()

            # Fuente para efectos
            self.effects_font = self.assets.get_font(18, bold=True)

            print("✓ Vista inicializada correctamente")
            return True

        except Exception as e:
            print(f"✗ Error inicializando vista: {e}")
            return False

    def load_assets(self):
        """Carga todos los recursos necesarios."""
        # Imágenes
        self.assets.load_image("pez.png", (20, 20))
        self.assets.load_image("trucha.png", (35, 35))
        self.assets.load_image("tiburon.png", (45, 45))
        self.assets.load_image("alga.png", (14, 14))

        # Sonidos
        self.assets.load_sound("comer_planta.mp3")
        self.assets.load_sound("comer.mp3")
        self.assets.load_sound("morir.mp3")
        self.assets.load_sound("musica_fondo_mar.mp3")

    # ------------------------------------------------------------------
    #     GESTIÓN DE PARTIDAS (DATOS)
    # ------------------------------------------------------------------

    def set_save_slots(
        self, slots: List[Dict[str, Any]], selected_id: Optional[str] = None
    ):
        """Actualiza la lista de partidas y la selección actual (para dibujar la UI)."""
        self.save_slots = slots
        if selected_id and any(s["save_id"] == selected_id for s in slots):
            self.selected_save_id = selected_id
        else:
            # si el seleccionado ya no existe, no hay selección
            self.selected_save_id = None
        self.pending_delete_id = None

    # ------------------------------------------------------------------
    #           MANEJO DE EVENTOS
    # ------------------------------------------------------------------

    def handle_events(self) -> Optional[Any]:
        """
        Procesa eventos de Pygame.

        Retorna:
        - None si no hay acción relevante.
        - str para acciones simples ("quit", "toggle_pause", "start", "stop").
        - dict para acciones de gestión de partidas:
            {"type": "save_create", "name": ...}
            {"type": "save_select", "save_id": ...}
            {"type": "save_rename", "save_id": ..., "new_name": ...}
            {"type": "save_delete", "save_id": ...}
            {"type": "save_load", "save_id": ...}
        """
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.handle_click(event.pos)
                if action:
                    return action

            elif event.type == pygame.KEYDOWN:
                # Si estamos escribiendo en el campo de texto de partida, capturamos el input
                if self.text_input_active:
                    # ENTER = confirmar
                    if event.key == pygame.K_RETURN:
                        txt = self.text_input_value.strip()
                        if not txt:
                            # solo cerrar el input
                            self.text_input_active = False
                            self.text_input_mode = None
                            self.text_input_target_id = None
                            return None

                        if self.text_input_mode == "create":
                            self.text_input_active = False
                            self.text_input_mode = None
                            return {"type": "save_create", "name": txt}
                        elif self.text_input_mode == "rename" and self.text_input_target_id:
                            save_id = self.text_input_target_id
                            self.text_input_active = False
                            self.text_input_mode = None
                            self.text_input_target_id = None
                            return {
                                "type": "save_rename",
                                "save_id": save_id,
                                "new_name": txt,
                            }
                        return None

                    # BACKSPACE
                    elif event.key == pygame.K_BACKSPACE:
                        self.text_input_value = self.text_input_value[:-1]
                        return None

                    # ESC: cancelar edición (sin cerrar el juego)
                    elif event.key == pygame.K_ESCAPE:
                        self.text_input_active = False
                        self.text_input_mode = None
                        self.text_input_target_id = None
                        return None

                    # Cualquier otro carácter imprimible
                    else:
                        ch = event.unicode
                        if ch and ch.isprintable() and len(self.text_input_value) < 30:
                            self.text_input_value += ch
                        return None

                # Si no hay input activo, teclas globales
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                elif event.key == pygame.K_SPACE and self.simulation_running:
                    return "toggle_pause"

        return None

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Any]:
        """Procesa un clic del mouse."""
        # Si el clic está fuera del panel, no es UI
        if self.panel_rect.collidepoint(pos):
            # Botones principales (control de simulación)
            if not self.simulation_running and self.btn_start.collidepoint(pos):
                # Solo permitir START si hay partida seleccionada
                if self.selected_save_id is not None:
                    return "start"
                else:
                    return None
            elif self.simulation_running and self.btn_pause.collidepoint(pos):
                return "toggle_pause"
            elif self.simulation_running and self.btn_stop.collidepoint(pos):
                return "stop"

            # --- Gestión de partidas: campos y botones ---
            # Campo de texto
            input_rect = self.save_ui_rects.get("input")
            if input_rect and input_rect.collidepoint(pos):
                # Activar modo "crear" si no estamos renombrando explícitamente
                if self.text_input_mode != "rename":
                    self.text_input_mode = "create"
                    self.text_input_value = "" if not self.text_input_active else self.text_input_value
                self.text_input_active = True
                return None

            # Botón "Crear partida"
            create_btn = self.save_ui_rects.get("create_btn")
            if create_btn and create_btn.collidepoint(pos):
                txt = self.text_input_value.strip()
                if txt:
                    # Disparamos evento de creación
                    self.text_input_active = False
                    self.text_input_mode = None
                    self.text_input_target_id = None
                    return {"type": "save_create", "name": txt}
                return None

            # Botón "Cargar partida"
            load_btn = self.save_ui_rects.get("load_btn")
            if load_btn and load_btn.collidepoint(pos):
                if self.selected_save_id:
                    return {"type": "save_load", "save_id": self.selected_save_id}
                return None

            # Clic en filas de partidas, renombrar o eliminar
            slots_rects: Dict[str, Dict[str, pygame.Rect]] = self.save_ui_rects.get(
                "slots", {}
            )
            for save_id, rects in slots_rects.items():
                row_rect = rects.get("row")
                rename_rect = rects.get("rename")
                delete_rect = rects.get("delete")

                # Seleccionar partida
                if row_rect and row_rect.collidepoint(pos):
                    self.selected_save_id = save_id
                    self.pending_delete_id = None
                    self.text_input_active = False
                    self.text_input_mode = None
                    self.text_input_target_id = None
                    return {"type": "save_select", "save_id": save_id}

                # Renombrar
                if rename_rect and rename_rect.collidepoint(pos):
                    # Activar input con el nombre actual
                    slot = next(
                        (s for s in self.save_slots if s["save_id"] == save_id), None
                    )
                    if slot:
                        self.text_input_mode = "rename"
                        self.text_input_target_id = save_id
                        self.text_input_value = slot["save_name"]
                        self.text_input_active = True
                        self.pending_delete_id = None
                    return None

                # Eliminar (con confirmación simple)
                if delete_rect and delete_rect.collidepoint(pos):
                    if self.pending_delete_id == save_id:
                        # Segunda vez: confirmar
                        self.pending_delete_id = None
                        self.text_input_active = False
                        self.text_input_mode = None
                        self.text_input_target_id = None
                        return {"type": "save_delete", "save_id": save_id}
                    else:
                        # Primera vez: marcar para confirmar
                        self.pending_delete_id = save_id
                        return None

            # Botones de configuración de poblaciones (si la simulación NO está corriendo)
            if not self.simulation_running:
                for key, buttons in self.config_buttons.items():
                    if buttons["minus"].collidepoint(pos):
                        self.config[key] = max(0, self.config[key] - 1)
                        return "config_changed"
                    elif buttons["plus"].collidepoint(pos):
                        self.config[key] = min(
                            cfg.POPULATION_LIMITS[key]["max"], self.config[key] + 1
                        )
                        return "config_changed"

        return None

    # ------------------------------------------------------------------
    #              PARTÍCULAS Y EVENTOS VISUALES
    # ------------------------------------------------------------------

    def update_particles(self):
        """Actualiza las partículas de efectos."""
        self.particles = [p for p in self.particles if not p.update()]

    def add_particle(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        """Añade una partícula de efecto."""
        self.particles.append(Particle(x, y, text, color))

    def process_ecosystem_events(self, events: List[Dict]):
        """Procesa eventos del ecosistema para efectos visuales."""
        for event in events:
            if event["type"] == "eat":
                energy = int(event.get("energy", 0))
                eater = event.get("eater", "")
                color = cfg.EAT_COLOR

                if eater == "pez":
                    text = f"+{energy}"
                    sound = self.assets.load_sound("comer_planta.mp3")
                else:
                    text = f"+{energy}"
                    sound = self.assets.load_sound("comer.mp3")

                self.add_particle(event["position"][0], event["position"][1], text, color)
                if sound:
                    sound.play()

            elif event["type"] == "birth":
                species = event.get("species", "")
                emoji = "🐟" if species == "pez" else "🦈" if species == "tiburon" else "🐠"
                self.add_particle(
                    event["position"][0],
                    event["position"][1],
                    f"{emoji}+1",
                    cfg.BIRTH_COLOR,
                )

            elif event["type"] == "death":
                self.add_particle(
                    event["position"][0], event["position"][1], "💀", cfg.DEATH_COLOR
                )
                sound = self.assets.load_sound("morir.mp3")
                if sound:
                    sound.play()

    # ------------------------------------------------------------------
    #                       DIBUJADO GENERAL
    # ------------------------------------------------------------------

    def draw_background(self):
        """Dibuja el fondo del juego (gradiente de agua)."""
        for y in range(cfg.SCREEN_HEIGHT):
            ratio = y / cfg.SCREEN_HEIGHT
            r = int(cfg.WATER_LIGHT.r * (1 - ratio) + cfg.WATER_DARK.r * ratio)
            g = int(cfg.WATER_LIGHT.g * (1 - ratio) + cfg.WATER_DARK.g * ratio)
            b = int(cfg.WATER_LIGHT.b * (1 - ratio) + cfg.WATER_DARK.b * ratio)
            pygame.draw.line(
                self.screen, (r, g, b), (0, y), (cfg.GAME_AREA_WIDTH, y)
            )

    def draw_entity(self, entity, image_name: str, fallback_color: pygame.Color):
        """Dibuja una entidad en pantalla."""
        if entity.x > cfg.GAME_AREA_WIDTH - entity.width:
            return

        image = self.assets.load_image(image_name)
        if image:
            if hasattr(entity, "direction") and entity.direction == -1:
                image = pygame.transform.flip(image, True, False)
            self.screen.blit(image, (int(entity.x), int(entity.y)))
        else:
            center = (
                int(entity.x + entity.width // 2),
                int(entity.y + entity.height // 2),
            )
            radius = entity.width // 2
            pygame.draw.circle(self.screen, fallback_color, center, radius)

    def draw_ecosystem(self, ecosystem: Ecosystem):
        """Dibuja todo el ecosistema."""
        self.draw_background()

        all_entities: List[Any] = []
        all_entities.extend(ecosystem.plants)
        all_entities.extend(ecosystem.fish)
        all_entities.extend(ecosystem.trout)
        all_entities.extend(ecosystem.sharks)

        all_entities.sort(key=lambda e: e.y)

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
        """Dibuja el panel lateral con controles, partidas y estadísticas."""
        # Fondo del panel
        panel_surface = pygame.Surface(
            (cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA
        )
        panel_surface.fill(
            (
                *cfg.PANEL_BG[:3],
                cfg.PANEL_BG.a if hasattr(cfg.PANEL_BG, "a") else 230,
            )
        )
        self.screen.blit(panel_surface, (self.panel_rect.x, 0))

        # Fuentes
        title_font = self.assets.get_font(24, bold=True)
        normal_font = self.assets.get_font(18)
        small_font = self.assets.get_font(14)

        # Título principal
        title = title_font.render("Panel de Control", True, cfg.TEXT_TITLE)
        self.screen.blit(title, (self.panel_rect.x + 20, 20))

        # Botones principales
        self.draw_main_buttons()

        # Gestión de partidas
        start_y = self.btn_stop.bottom + 20
        next_y = self.draw_save_manager(small_font, normal_font, start_y)

        # Configuración o estadísticas según el estado
        if self.simulation_running:
            self.draw_statistics(ecosystem, small_font, normal_font, next_y + 10)
        else:
            self.draw_configuration(small_font, normal_font, next_y + 10)

    def draw_main_buttons(self):
        """Dibuja los botones principales."""
        # START solo visible si no está corriendo
        if not self.simulation_running:
            start_enabled = self.selected_save_id is not None
            self.draw_button(self.btn_start, "Comenzar", cfg.BTN_START, start_enabled)

        # PAUSE / STOP solo si está corriendo
        if self.simulation_running:
            pause_text = "Pausar" if not self.simulation_paused else "Reanudar"
            pause_color = (
                cfg.BTN_PAUSE if not self.simulation_paused else cfg.BTN_RESUME
            )
            self.draw_button(self.btn_pause, pause_text, pause_color, True)
            self.draw_button(self.btn_stop, "Detener", cfg.BTN_STOP, True)

    def draw_button(
        self, rect: pygame.Rect, text: str, color: pygame.Color, enabled: bool
    ):
        """Dibuja un botón con efecto hover."""
        btn_color = color

        mouse_pos = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse_pos)

        if hover and enabled:
            btn_color = (
                min(255, color.r + 30),
                min(255, color.g + 30),
                min(255, color.b + 30),
            )

        if not enabled:
            btn_color = (color.r // 2, color.g // 2, color.b // 2)

        pygame.draw.rect(self.screen, btn_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=8)

        font = self.assets.get_font(18)
        text_surface = font.render(text, True, cfg.BTN_TEXT)
        text_rect = text_surface.get_rect(center=rect.center)
        self.screen.blit(text_surface, text_rect)

    # ------------------------------------------------------------------
    #                DIBUJO: GESTOR DE PARTIDAS
    # ------------------------------------------------------------------

    def draw_save_manager(
        self,
        small_font: pygame.font.Font,
        normal_font: pygame.font.Font,
        start_y: int,
    ) -> int:
        """
        Dibuja la sección de gestión de partidas.
        Retorna el Y final para seguir dibujando debajo.
        """
        x = self.panel_rect.x + 20
        y = start_y

        title = normal_font.render("Gestión de Partidas", True, cfg.TEXT_TITLE)
        self.screen.blit(title, (x, y))
        y += 30

        # Campo de texto para nombre de partida
        input_rect = pygame.Rect(x, y, cfg.PANEL_WIDTH - 130, 28)
        create_rect = pygame.Rect(input_rect.right + 8, y, 80, 28)

        self.save_ui_rects["input"] = input_rect
        self.save_ui_rects["create_btn"] = create_rect

        # Fondo del input
        pygame.draw.rect(self.screen, cfg.BAR_BG, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, cfg.SEPARATOR, input_rect, 1, border_radius=4)

        # Texto dentro del input
        if self.text_input_active and self.text_input_mode in ("create", "rename"):
            text = self.text_input_value
        else:
            text = ""
        placeholder = "Nombre partida..." if not text else text
        color = cfg.TEXT_NORMAL if text else cfg.SEPARATOR

        input_text_surface = small_font.render(placeholder, True, color)
        self.screen.blit(input_text_surface, (input_rect.x + 6, input_rect.y + 6))

        # Botón "Crear"
        self.draw_button(create_rect, "Crear", cfg.BTN_PLUS, True)

        y += 40

        # Título de lista
        list_title = small_font.render("Partidas guardadas:", True, cfg.TEXT_NORMAL)
        self.screen.blit(list_title, (x, y))
        y += 20

        # Lista de partidas
        self.save_ui_rects["slots"] = {}
        row_height = 28
        max_rows = 5  # para no desbordar verticalmente (simple)

        for idx, slot in enumerate(self.save_slots[:max_rows]):
            save_id = slot["save_id"]
            name = slot["save_name"]

            row_rect = pygame.Rect(x, y, cfg.PANEL_WIDTH - 40, row_height)
            rename_rect = pygame.Rect(row_rect.right - 56, y + 2, 24, row_height - 4)
            delete_rect = pygame.Rect(row_rect.right - 28, y + 2, 24, row_height - 4)

            # Fondo de fila (selección)
            if self.selected_save_id == save_id:
                pygame.draw.rect(self.screen, cfg.BAR_BG, row_rect, border_radius=4)
            else:
                pygame.draw.rect(
                    self.screen, (30, 34, 38), row_rect, border_radius=4
                )

            # Nombre (recortado si es largo)
            display_name = name
            if len(display_name) > 18:
                display_name = display_name[:16] + "…"

            name_surface = small_font.render(display_name, True, cfg.TEXT_TITLE)
            self.screen.blit(name_surface, (row_rect.x + 6, row_rect.y + 6))

            # Botón R (rename)
            pygame.draw.rect(self.screen, cfg.BTN_PAUSE, rename_rect, border_radius=6)
            r_text = small_font.render("R", True, cfg.BTN_TEXT)
            r_rect = r_text.get_rect(center=rename_rect.center)
            self.screen.blit(r_text, r_rect)

            # Botón X (delete)
            pygame.draw.rect(self.screen, cfg.BTN_STOP, delete_rect, border_radius=6)
            x_text = small_font.render("X", True, cfg.BTN_TEXT)
            x_rect = x_text.get_rect(center=delete_rect.center)
            self.screen.blit(x_text, x_rect)

            self.save_ui_rects["slots"][save_id] = {
                "row": row_rect,
                "rename": rename_rect,
                "delete": delete_rect,
            }

            y += row_height + 4

        # Mensaje de confirmación de borrado
        if self.pending_delete_id:
            warn_text = small_font.render(
                "Click de nuevo en X para eliminar.", True, cfg.BTN_STOP
            )
            self.screen.blit(warn_text, (x, y))
            y += 20

        # Botón "Cargar partida"
        load_rect = pygame.Rect(x, y + 4, cfg.PANEL_WIDTH - 40, 30)
        self.save_ui_rects["load_btn"] = load_rect
        load_enabled = self.selected_save_id is not None
        self.draw_button(load_rect, "Cargar partida", cfg.BTN_RESUME, load_enabled)

        return load_rect.bottom

    # ------------------------------------------------------------------
    #           DIBUJO: CONFIGURACIÓN Y ESTADÍSTICAS
    # ------------------------------------------------------------------

    def draw_configuration(
        self, small_font: pygame.font.Font, normal_font: pygame.font.Font, start_y: int
    ):
        """Dibuja la configuración inicial con botones + y -."""
        x = self.panel_rect.x + 20
        y = start_y

        config_title = normal_font.render("Configuración Inicial", True, cfg.TEXT_TITLE)
        self.screen.blit(config_title, (x, y))
        y += 40

        for key, buttons in self.config_buttons.items():
            # Mover las filas en función de y inicial (solo usamos el label como referencia)
            label_surface = small_font.render(buttons["label"], True, cfg.TEXT_NORMAL)
            self.screen.blit(label_surface, (x, buttons["minus"].y))

            # Botón -
            minus_color = (
                cfg.BTN_MINUS if self.config[key] > 0 else (100, 100, 100)
            )
            self.draw_button(
                buttons["minus"], "-", minus_color, self.config[key] > 0
            )

            # Valor
            value_surface = normal_font.render(str(self.config[key]), True, cfg.TEXT_TITLE)
            value_rect = value_surface.get_rect(center=buttons["value"].center)
            self.screen.blit(value_surface, value_rect)

            # Botón +
            plus_color = (
                cfg.BTN_PLUS
                if self.config[key] < cfg.POPULATION_LIMITS[key]["max"]
                else (100, 100, 100)
            )
            self.draw_button(
                buttons["plus"],
                "+",
                plus_color,
                self.config[key] < cfg.POPULATION_LIMITS[key]["max"],
            )

    def draw_statistics(
        self,
        ecosystem: Ecosystem,
        small_font: pygame.font.Font,
        normal_font: pygame.font.Font,
        start_y: int,
    ):
        """Dibuja las estadísticas de la simulación."""
        x = self.panel_rect.x + 20
        y = start_y

        stats_title = normal_font.render("Estadísticas", True, cfg.TEXT_TITLE)
        self.screen.blit(stats_title, (x, y))
        y += 40

        stats = ecosystem.get_statistics()

        populations = [
            ("Algas", stats["plants"], cfg.GREEN, 50),
            ("Peces", stats["fish"], cfg.BLUE, 30),
            ("Truchas", stats["trout"], cfg.BROWN, 15),
            ("Tiburones", stats["sharks"], cfg.GRAY, 10),
        ]

        for label, count, color, max_count in populations:
            text = f"{label} ({count})"
            text_surface = small_font.render(text, True, cfg.TEXT_NORMAL)
            self.screen.blit(text_surface, (x, y))
            y += 20

            progress = count / max(1, max_count)
            bar_width = cfg.PANEL_WIDTH - 40
            bar_height = 8

            pygame.draw.rect(
                self.screen,
                cfg.BAR_BG,
                (x, y, bar_width, bar_height),
                border_radius=4,
            )

            if progress > 0:
                fill_width = int(bar_width * progress)
                pygame.draw.rect(
                    self.screen,
                    color,
                    (x, y, fill_width, bar_height),
                    border_radius=4,
                )

            y += 25

        # Información de tiempo
        y += 10
        time_text = f"Día {stats['day']} · {stats['time_of_day'].capitalize()}"
        time_surface = small_font.render(time_text, True, cfg.TEXT_NORMAL)
        self.screen.blit(time_surface, (x, y))
        y += 20

        # Barra de progreso del día
        day_bar_width = cfg.PANEL_WIDTH - 40
        pygame.draw.rect(
            self.screen,
            cfg.BAR_BG,
            (x, y, day_bar_width, 6),
            border_radius=3,
        )
        if stats["day_progress"] > 0:
            fill = int(day_bar_width * stats["day_progress"])
            pygame.draw.rect(
                self.screen,
                cfg.BAR_PROGRESS,
                (x, y, fill, 6),
                border_radius=3,
            )
        y += 15

        # Estación
        season_text = f"Estación: {stats['season']}"
        season_surface = small_font.render(season_text, True, cfg.TEXT_TITLE)
        self.screen.blit(season_surface, (x, y))
        y += 20

        # Barra de progreso del turno IA
        y += 10
        turn_text = small_font.render("Siguiente turno IA:", True, cfg.TEXT_NORMAL)
        self.screen.blit(turn_text, (x, y))
        y += 20

        turn_bar_width = cfg.PANEL_WIDTH - 40
        pygame.draw.rect(
            self.screen,
            cfg.BAR_BG,
            (x, y, turn_bar_width, 8),
            border_radius=4,
        )
        if self.turn_progress > 0:
            fill = int(turn_bar_width * self.turn_progress)
            pygame.draw.rect(
                self.screen,
                cfg.BAR_PROGRESS,
                (x, y, fill, 8),
                border_radius=4,
            )

    # ------------------------------------------------------------------
    #                         PAUSA Y RENDER
    # ------------------------------------------------------------------

    def draw_particles(self):
        """Dibuja las partículas de efectos."""
        for particle in self.particles:
            particle.draw(self.screen, self.effects_font)

    def draw_pause_overlay(self):
        """Dibuja el overlay de pausa."""
        if not self.simulation_paused:
            return

        overlay = pygame.Surface((cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        font = self.assets.get_font(72, bold=True)
        text = font.render("PAUSA", True, cfg.WHITE)
        text_rect = text.get_rect(
            center=(cfg.GAME_AREA_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
        )
        self.screen.blit(text, text_rect)

    def render(self, ecosystem: Ecosystem):
        """Renderiza el frame completo."""
        self.screen.fill(cfg.BLACK)

        self.draw_ecosystem(ecosystem)
        self.draw_particles()
        self.draw_panel(ecosystem)
        self.draw_pause_overlay()

        pygame.display.flip()
        self.clock.tick(cfg.FPS)

    # ------------------------------------------------------------------
    #              MÉTODOS AUXILIARES PARA CONTROLADOR
    # ------------------------------------------------------------------

    def set_turn_progress(self, progress: float):
        """Establece el progreso del turno para la barra UI."""
        self.turn_progress = max(0.0, min(1.0, progress))

    def set_simulation_state(self, running: bool, paused: bool):
        """Establece el estado de la simulación para la UI."""
        self.simulation_running = running
        self.simulation_paused = paused

    def get_configuration(self) -> Dict[str, int]:
        """Obtiene la configuración actual de poblaciones."""
        return self.config.copy()

    def cleanup(self):
        """Limpia los recursos."""
        pygame.mixer.quit()
        pygame.quit()
