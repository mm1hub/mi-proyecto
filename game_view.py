"""
Sistema de visualización del juego.
Maneja la ventana, renderizado y efectos visuales.
"""

import os
import pygame
from typing import List, Dict, Tuple, Optional, Any

import config as cfg
from game_logic import Ecosystem, Plant, Fish, Trout, Shark


class AssetLoader:
    def __init__(self):
        self.images: Dict[str, pygame.Surface] = {}
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.fonts: Dict[str, pygame.font.Font] = {}

    def load_image(self, filename: str, size: Tuple[int, int] = None) -> Optional[pygame.Surface]:
        if filename in self.images:
            return self.images[filename]
        path = os.path.join("assets", filename)
        if not os.path.exists(path):
            print(f"⚠️  Imagen no encontrada: {path}")
            return None
        try:
            img = pygame.image.load(path).convert_alpha()
            if size:
                img = pygame.transform.scale(img, size)
            self.images[filename] = img
            return img
        except Exception as e:
            print(f"✗ Error cargando imagen {filename}: {e}")
            return None

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        if filename in self.sounds:
            return self.sounds[filename]
        path = os.path.join("assets", filename)
        if not os.path.exists(path):
            print(f"⚠️  Sonido no encontrado: {path}")
            return None
        try:
            s = pygame.mixer.Sound(path)
            self.sounds[filename] = s
            return s
        except Exception as e:
            print(f"✗ Error cargando sonido {filename}: {e}")
            return None

    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = f"{size}_{bold}"
        if key not in self.fonts:
            try:
                self.fonts[key] = pygame.font.SysFont("Arial", size, bold=bold)
            except Exception:
                self.fonts[key] = pygame.font.Font(None, size)
        return self.fonts[key]


class Particle:
    def __init__(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 60
        self.speed_y = -1.5

    def update(self) -> bool:
        self.y += self.speed_y
        self.life -= 1
        return self.life <= 0

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        alpha = min(255, self.life * 4)
        surf = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        screen.blit(surf, (int(self.x), int(self.y)))


class GameView:
    def __init__(self):
        self.screen: Optional[pygame.Surface] = None
        self.clock: Optional[pygame.time.Clock] = None
        self.assets = AssetLoader()
        self.particles: List[Particle] = []
        self.effects_font: Optional[pygame.font.Font] = None

        self.simulation_running = False
        self.simulation_paused = False

        self.panel_rect = pygame.Rect(cfg.SCREEN_WIDTH - cfg.PANEL_WIDTH, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT)

        # Botones control
        self.setup_main_buttons()

        # Botones config (+/-)
        self.config_buttons: Dict[str, Dict[str, Any]] = {}
        self.setup_config_buttons()

        self.config: Dict[str, int] = {
            "plantas": cfg.DEFAULT_POPULATION["plantas"],
            "peces": cfg.DEFAULT_POPULATION["peces"],
            "truchas": cfg.DEFAULT_POPULATION["truchas"],
            "tiburones": cfg.DEFAULT_POPULATION["tiburones"],
        }

        self.turn_progress = 0.0

        # Gestión partidas
        self.save_slots: List[Dict[str, Any]] = []
        self.selected_save_id: Optional[str] = None
        self.active_save_name: str = ""  # <-- para mostrar arriba izq

        self.pending_delete_id: Optional[str] = None

        # Input texto
        self.text_input_active = False
        self.text_input_value: str = ""
        self.text_input_mode: Optional[str] = None  # "create" / "rename"
        self.text_input_target_id: Optional[str] = None

        self.save_ui_rects: Dict[str, Any] = {"input": None, "create_btn": None, "load_btn": None, "slots": {}}

    # ----------------- setup botones -----------------

    def setup_main_buttons(self):
        padding = 20
        x = self.panel_rect.x + padding
        y = padding + 40
        w = cfg.PANEL_WIDTH - (padding * 2)
        h = 40

        self.btn_start = pygame.Rect(x, y, w, h)
        self.btn_pause = pygame.Rect(x, y + h + 10, w, h)
        self.btn_stop = pygame.Rect(x, y + (h + 10) * 2, w, h)
        # NUEVO: botón guardado manual bajo stop
        self.btn_manual_save = pygame.Rect(x, y + (h + 10) * 3, w, 36)

    def setup_config_buttons(self):
        padding = 20
        x = self.panel_rect.x + padding
        # OJO: lo definimos más abajo porque ahora hay btn_manual_save cuando corre
        y = self.btn_stop.bottom + 220

        items = [
            ("plantas", "🌿 Algas", y),
            ("peces", "🐟 Peces", y + 50),
            ("truchas", "🐠 Truchas", y + 100),
            ("tiburones", "🦈 Tiburones", y + 150),
        ]

        for k, label, y_pos in items:
            minus = pygame.Rect(x, y_pos, 30, 30)
            plus = pygame.Rect(x + cfg.PANEL_WIDTH - padding - 30, y_pos, 30, 30)
            value = pygame.Rect(x + 40, y_pos, cfg.PANEL_WIDTH - padding * 2 - 80, 30)
            self.config_buttons[k] = {"minus": minus, "plus": plus, "value": value, "label": label}

    # ----------------- init assets -----------------

    def initialize(self) -> bool:
        try:
            pygame.init()
            pygame.display.set_caption("Simulador de Ecosistema Acuático")
            self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
            self.clock = pygame.time.Clock()
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

            self.load_assets()
            self.effects_font = self.assets.get_font(18, bold=True)

            print("✓ Vista inicializada correctamente")
            return True
        except Exception as e:
            print(f"✗ Error inicializando vista: {e}")
            return False

    def load_assets(self):
        self.assets.load_image("pez.png", (20, 20))
        self.assets.load_image("trucha.png", (35, 35))
        self.assets.load_image("tiburon.png", (45, 45))
        self.assets.load_image("alga.png", (14, 14))

        self.assets.load_sound("comer_planta.mp3")
        self.assets.load_sound("comer.mp3")
        self.assets.load_sound("morir.mp3")
        self.assets.load_sound("musica_fondo_mar.mp3")

    # ----------------- API desde controlador -----------------

    def set_save_slots(self, slots: List[Dict[str, Any]], selected_id: Optional[str] = None):
        self.save_slots = slots
        if selected_id and any(s["save_id"] == selected_id for s in slots):
            self.selected_save_id = selected_id
        elif self.selected_save_id and not any(s["save_id"] == self.selected_save_id for s in slots):
            self.selected_save_id = None
        self.pending_delete_id = None

    def set_active_save_name(self, name: str):
        self.active_save_name = name or ""

    # ----------------- eventos -----------------

    def handle_events(self) -> Optional[Any]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                act = self.handle_click(event.pos)
                if act:
                    return act

            elif event.type == pygame.KEYDOWN:
                if self.text_input_active:
                    if event.key == pygame.K_RETURN:
                        txt = self.text_input_value.strip()
                        if not txt:
                            self.text_input_active = False
                            self.text_input_mode = None
                            self.text_input_target_id = None
                            return None

                        if self.text_input_mode == "create":
                            self.text_input_active = False
                            self.text_input_mode = None
                            return {"type": "save_create", "name": txt}

                        if self.text_input_mode == "rename" and self.text_input_target_id:
                            save_id = self.text_input_target_id
                            self.text_input_active = False
                            self.text_input_mode = None
                            self.text_input_target_id = None
                            return {"type": "save_rename", "save_id": save_id, "new_name": txt}

                        return None

                    elif event.key == pygame.K_BACKSPACE:
                        self.text_input_value = self.text_input_value[:-1]
                        return None

                    elif event.key == pygame.K_ESCAPE:
                        self.text_input_active = False
                        self.text_input_mode = None
                        self.text_input_target_id = None
                        return None

                    else:
                        ch = event.unicode
                        if ch and ch.isprintable() and len(self.text_input_value) < 30:
                            self.text_input_value += ch
                        return None

                # global keys
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                elif event.key == pygame.K_SPACE and self.simulation_running:
                    return "toggle_pause"

        return None

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Any]:
        if not self.panel_rect.collidepoint(pos):
            # click fuera del panel: si estaba esperando confirmación delete, la cancelamos
            self.pending_delete_id = None
            return None

        # Botón guardado manual (solo cuando corre y hay partida seleccionada)
        if self.simulation_running and self.selected_save_id and self.btn_manual_save.collidepoint(pos):
            return {"type": "save_manual", "save_id": self.selected_save_id}

        # controles principales
        if not self.simulation_running and self.btn_start.collidepoint(pos):
            if self.selected_save_id is not None:
                return "start"
            return None

        if self.simulation_running and self.btn_pause.collidepoint(pos):
            return "toggle_pause"

        if self.simulation_running and self.btn_stop.collidepoint(pos):
            return "stop"

        # input create
        input_rect = self.save_ui_rects.get("input")
        if input_rect and input_rect.collidepoint(pos):
            if self.text_input_mode != "rename":
                self.text_input_mode = "create"
                if not self.text_input_active:
                    self.text_input_value = ""
            self.text_input_active = True
            return None

        create_btn = self.save_ui_rects.get("create_btn")
        if create_btn and create_btn.collidepoint(pos):
            txt = self.text_input_value.strip()
            if txt:
                self.text_input_active = False
                self.text_input_mode = None
                self.text_input_target_id = None
                return {"type": "save_create", "name": txt}
            return None

        load_btn = self.save_ui_rects.get("load_btn")
        if load_btn and load_btn.collidepoint(pos):
            if self.selected_save_id:
                return {"type": "save_load", "save_id": self.selected_save_id}
            return None

        # filas partidas
        slots_rects: Dict[str, Dict[str, pygame.Rect]] = self.save_ui_rects.get("slots", {})

        for save_id, rects in slots_rects.items():
            row_rect = rects.get("row")
            rename_rect = rects.get("rename")
            delete_rect = rects.get("delete")

            # ✅ FIX CRÍTICO: primero rename/delete y recién después seleccionar fila
            if rename_rect and rename_rect.collidepoint(pos):
                slot = next((s for s in self.save_slots if s["save_id"] == save_id), None)
                if slot:
                    self.text_input_mode = "rename"
                    self.text_input_target_id = save_id
                    self.text_input_value = slot["save_name"]
                    self.text_input_active = True
                    self.pending_delete_id = None
                return None

            if delete_rect and delete_rect.collidepoint(pos):
                if self.pending_delete_id == save_id:
                    self.pending_delete_id = None
                    self.text_input_active = False
                    self.text_input_mode = None
                    self.text_input_target_id = None
                    return {"type": "save_delete", "save_id": save_id}
                else:
                    self.pending_delete_id = save_id
                    return None

            if row_rect and row_rect.collidepoint(pos):
                self.selected_save_id = save_id
                self.pending_delete_id = None
                self.text_input_active = False
                self.text_input_mode = None
                self.text_input_target_id = None
                return {"type": "save_select", "save_id": save_id}

        # config (+/-) solo si NO corre
        if not self.simulation_running:
            for key, buttons in self.config_buttons.items():
                if buttons["minus"].collidepoint(pos):
                    self.config[key] = max(0, self.config[key] - 1)
                    return "config_changed"
                if buttons["plus"].collidepoint(pos):
                    self.config[key] = min(cfg.POPULATION_LIMITS[key]["max"], self.config[key] + 1)
                    return "config_changed"

        return None

    # ----------------- partículas y eventos -----------------

    def update_particles(self):
        self.particles = [p for p in self.particles if not p.update()]

    def add_particle(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.particles.append(Particle(x, y, text, color))

    def process_ecosystem_events(self, events: List[Dict]):
        for event in events:
            if event["type"] == "eat":
                energy = int(event.get("energy", 0))
                eater = event.get("eater", "")
                if eater == "pez":
                    snd = self.assets.load_sound("comer_planta.mp3")
                else:
                    snd = self.assets.load_sound("comer.mp3")
                self.add_particle(event["position"][0], event["position"][1], f"+{energy}", cfg.EAT_COLOR)
                if snd:
                    snd.play()

            elif event["type"] == "birth":
                species = event.get("species", "")
                emoji = "🐟" if species == "pez" else "🦈" if species == "tiburon" else "🐠"
                self.add_particle(event["position"][0], event["position"][1], f"{emoji}+1", cfg.BIRTH_COLOR)

            elif event["type"] == "death":
                self.add_particle(event["position"][0], event["position"][1], "💀", cfg.DEATH_COLOR)
                snd = self.assets.load_sound("morir.mp3")
                if snd:
                    snd.play()

    # ----------------- dibujado -----------------

    def draw_background(self):
        for y in range(cfg.SCREEN_HEIGHT):
            ratio = y / cfg.SCREEN_HEIGHT
            r = int(cfg.WATER_LIGHT.r * (1 - ratio) + cfg.WATER_DARK.r * ratio)
            g = int(cfg.WATER_LIGHT.g * (1 - ratio) + cfg.WATER_DARK.g * ratio)
            b = int(cfg.WATER_LIGHT.b * (1 - ratio) + cfg.WATER_DARK.b * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (cfg.GAME_AREA_WIDTH, y))

    def draw_entity(self, entity, image_name: str, fallback_color: pygame.Color):
        if entity.x > cfg.GAME_AREA_WIDTH - entity.width:
            return
        img = self.assets.load_image(image_name)
        if img:
            if hasattr(entity, "direction") and entity.direction == -1:
                img = pygame.transform.flip(img, True, False)
            self.screen.blit(img, (int(entity.x), int(entity.y)))
        else:
            center = (int(entity.x + entity.width // 2), int(entity.y + entity.height // 2))
            pygame.draw.circle(self.screen, fallback_color, center, entity.width // 2)

    def draw_ecosystem(self, ecosystem: Ecosystem):
        self.draw_background()
        all_entities: List[Any] = []
        all_entities.extend(ecosystem.plants)
        all_entities.extend(ecosystem.fish)
        all_entities.extend(ecosystem.trout)
        all_entities.extend(ecosystem.sharks)
        all_entities.sort(key=lambda e: e.y)

        for e in all_entities:
            if isinstance(e, Plant):
                self.draw_entity(e, "alga.png", cfg.GREEN)
            elif isinstance(e, Fish):
                self.draw_entity(e, "pez.png", cfg.BLUE)
            elif isinstance(e, Trout):
                self.draw_entity(e, "trucha.png", cfg.BROWN)
            elif isinstance(e, Shark):
                self.draw_entity(e, "tiburon.png", cfg.GRAY)

    def draw_active_save_label(self):
        """NUEVO: texto arriba-izq durante simulación con partida activa."""
        if not self.simulation_running or not self.active_save_name:
            return
        font = self.assets.get_font(18, bold=True)
        txt = f"Partida: {self.active_save_name}"
        surf = font.render(txt, True, cfg.TEXT_TITLE)

        # fondo semitransparente para legibilidad
        pad = 8
        bg = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad * 2), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 120))
        self.screen.blit(bg, (10, 10))
        self.screen.blit(surf, (10 + pad, 10 + pad))

    def draw_panel(self, ecosystem: Ecosystem):
        panel = pygame.Surface((cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        panel.fill((*cfg.PANEL_BG[:3], cfg.PANEL_BG.a if hasattr(cfg.PANEL_BG, "a") else 230))
        self.screen.blit(panel, (self.panel_rect.x, 0))

        title_font = self.assets.get_font(24, bold=True)
        normal_font = self.assets.get_font(18)
        small_font = self.assets.get_font(14)

        self.screen.blit(title_font.render("Panel de Control", True, cfg.TEXT_TITLE), (self.panel_rect.x + 20, 20))

        self.draw_main_buttons()

        # dónde empieza la gestión (si corre, deja espacio para btn_manual_save)
        controls_bottom = self.btn_manual_save.bottom if self.simulation_running else self.btn_stop.bottom
        start_y = controls_bottom + 14

        next_y = self.draw_save_manager(small_font, normal_font, start_y)

        if self.simulation_running:
            self.draw_statistics(ecosystem, small_font, normal_font, next_y + 10)
        else:
            self.draw_configuration(small_font, normal_font, next_y + 10)

    def draw_main_buttons(self):
        if not self.simulation_running:
            enabled = self.selected_save_id is not None
            self.draw_button(self.btn_start, "Comenzar", cfg.BTN_START, enabled)

        if self.simulation_running:
            pause_text = "Pausar" if not self.simulation_paused else "Reanudar"
            pause_color = cfg.BTN_PAUSE if not self.simulation_paused else cfg.BTN_RESUME
            self.draw_button(self.btn_pause, pause_text, pause_color, True)
            self.draw_button(self.btn_stop, "Detener", cfg.BTN_STOP, True)

            # NUEVO: Guardado manual (solo si hay partida seleccionada)
            can_save = self.selected_save_id is not None
            self.draw_button(self.btn_manual_save, "Guardar (Manual)", cfg.BTN_PLUS, can_save)

    def draw_button(self, rect: pygame.Rect, text: str, color: pygame.Color, enabled: bool):
        btn_color = color
        hover = rect.collidepoint(pygame.mouse.get_pos())

        if hover and enabled:
            btn_color = (min(255, color.r + 30), min(255, color.g + 30), min(255, color.b + 30))
        if not enabled:
            btn_color = (color.r // 2, color.g // 2, color.b // 2)

        pygame.draw.rect(self.screen, btn_color, rect, border_radius=8)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=8)

        font = self.assets.get_font(18)
        surf = font.render(text, True, cfg.BTN_TEXT)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_save_manager(self, small_font, normal_font, start_y: int) -> int:
        x = self.panel_rect.x + 20
        y = start_y

        self.screen.blit(normal_font.render("Gestión de Partidas", True, cfg.TEXT_TITLE), (x, y))
        y += 30

        input_rect = pygame.Rect(x, y, cfg.PANEL_WIDTH - 130, 28)
        create_rect = pygame.Rect(input_rect.right + 8, y, 80, 28)
        self.save_ui_rects["input"] = input_rect
        self.save_ui_rects["create_btn"] = create_rect

        pygame.draw.rect(self.screen, cfg.BAR_BG, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, cfg.SEPARATOR, input_rect, 1, border_radius=4)

        if self.text_input_active and self.text_input_mode in ("create", "rename"):
            text = self.text_input_value
        else:
            text = ""
        placeholder = "Nombre partida..." if not text else text
        color = cfg.TEXT_NORMAL if text else cfg.SEPARATOR
        self.screen.blit(small_font.render(placeholder, True, color), (input_rect.x + 6, input_rect.y + 6))

        self.draw_button(create_rect, "Crear", cfg.BTN_PLUS, True)
        y += 40

        self.screen.blit(small_font.render("Partidas guardadas:", True, cfg.TEXT_NORMAL), (x, y))
        y += 20

        self.save_ui_rects["slots"] = {}
        row_h = 28
        max_rows = 5

        for slot in self.save_slots[:max_rows]:
            save_id = slot["save_id"]
            name = slot["save_name"]

            row_rect = pygame.Rect(x, y, cfg.PANEL_WIDTH - 40, row_h)
            rename_rect = pygame.Rect(row_rect.right - 56, y + 2, 24, row_h - 4)
            delete_rect = pygame.Rect(row_rect.right - 28, y + 2, 24, row_h - 4)

            bg = cfg.BAR_BG if self.selected_save_id == save_id else (30, 34, 38)
            pygame.draw.rect(self.screen, bg, row_rect, border_radius=4)

            display = name if len(name) <= 18 else name[:16] + "…"
            self.screen.blit(small_font.render(display, True, cfg.TEXT_TITLE), (row_rect.x + 6, row_rect.y + 6))

            pygame.draw.rect(self.screen, cfg.BTN_PAUSE, rename_rect, border_radius=6)
            r = small_font.render("R", True, cfg.BTN_TEXT)
            self.screen.blit(r, r.get_rect(center=rename_rect.center))

            pygame.draw.rect(self.screen, cfg.BTN_STOP, delete_rect, border_radius=6)
            x_txt = small_font.render("X", True, cfg.BTN_TEXT)
            self.screen.blit(x_txt, x_txt.get_rect(center=delete_rect.center))

            self.save_ui_rects["slots"][save_id] = {"row": row_rect, "rename": rename_rect, "delete": delete_rect}
            y += row_h + 4

        if self.pending_delete_id:
            self.screen.blit(
                small_font.render("Click de nuevo en X para eliminar.", True, cfg.BTN_STOP),
                (x, y),
            )
            y += 20

        load_rect = pygame.Rect(x, y + 4, cfg.PANEL_WIDTH - 40, 30)
        self.save_ui_rects["load_btn"] = load_rect
        self.draw_button(load_rect, "Cargar partida", cfg.BTN_RESUME, self.selected_save_id is not None)

        return load_rect.bottom

    def draw_configuration(self, small_font, normal_font, start_y: int):
        x = self.panel_rect.x + 20
        self.screen.blit(normal_font.render("Configuración Inicial", True, cfg.TEXT_TITLE), (x, start_y))

        for key, buttons in self.config_buttons.items():
            self.screen.blit(small_font.render(buttons["label"], True, cfg.TEXT_NORMAL), (x, buttons["minus"].y))

            minus_color = cfg.BTN_MINUS if self.config[key] > 0 else (100, 100, 100)
            self.draw_button(buttons["minus"], "-", minus_color, self.config[key] > 0)

            val = normal_font.render(str(self.config[key]), True, cfg.TEXT_TITLE)
            self.screen.blit(val, val.get_rect(center=buttons["value"].center))

            plus_color = cfg.BTN_PLUS if self.config[key] < cfg.POPULATION_LIMITS[key]["max"] else (100, 100, 100)
            self.draw_button(buttons["plus"], "+", plus_color, self.config[key] < cfg.POPULATION_LIMITS[key]["max"])

    def draw_statistics(self, ecosystem: Ecosystem, small_font, normal_font, start_y: int):
        x = self.panel_rect.x + 20
        y = start_y

        self.screen.blit(normal_font.render("Estadísticas", True, cfg.TEXT_TITLE), (x, y))
        y += 40

        stats = ecosystem.get_statistics()
        populations = [
            ("Algas", stats["plants"], cfg.GREEN, 50),
            ("Peces", stats["fish"], cfg.BLUE, 30),
            ("Truchas", stats["trout"], cfg.BROWN, 15),
            ("Tiburones", stats["sharks"], cfg.GRAY, 10),
        ]

        for label, count, color, max_count in populations:
            self.screen.blit(small_font.render(f"{label} ({count})", True, cfg.TEXT_NORMAL), (x, y))
            y += 20

            progress = count / max(1, max_count)
            w = cfg.PANEL_WIDTH - 40
            pygame.draw.rect(self.screen, cfg.BAR_BG, (x, y, w, 8), border_radius=4)
            if progress > 0:
                pygame.draw.rect(self.screen, color, (x, y, int(w * progress), 8), border_radius=4)
            y += 25

    def draw_particles(self):
        for p in self.particles:
            p.draw(self.screen, self.effects_font)

    def draw_pause_overlay(self):
        if not self.simulation_paused:
            return
        overlay = pygame.Surface((cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))
        font = self.assets.get_font(72, bold=True)
        surf = font.render("PAUSA", True, cfg.WHITE)
        self.screen.blit(surf, surf.get_rect(center=(cfg.GAME_AREA_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)))

    def render(self, ecosystem: Ecosystem):
        self.screen.fill(cfg.BLACK)
        self.draw_ecosystem(ecosystem)
        self.draw_particles()
        self.draw_active_save_label()   # <-- NUEVO: arriba izq
        self.draw_panel(ecosystem)
        self.draw_pause_overlay()
        pygame.display.flip()
        self.clock.tick(cfg.FPS)

    # ----------------- helpers controlador -----------------

    def set_turn_progress(self, progress: float):
        self.turn_progress = max(0.0, min(1.0, progress))

    def set_simulation_state(self, running: bool, paused: bool):
        self.simulation_running = running
        self.simulation_paused = paused

    def get_configuration(self) -> Dict[str, int]:
        return self.config.copy()

    def cleanup(self):
        pygame.mixer.quit()
        pygame.quit()
