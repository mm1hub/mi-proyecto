"""
Sistema de visualización del juego.
Interfaz Gráfica Minimalista y Escalable.
CORREGIDO: draw_particles restaurado.
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
        if filename in self.images: return self.images[filename]
        path = os.path.join("assets", filename)
        if not os.path.exists(path): return None
        try:
            img = pygame.image.load(path).convert_alpha()
            if size: img = pygame.transform.scale(img, size)
            self.images[filename] = img
            return img
        except Exception: return None

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        if filename in self.sounds: return self.sounds[filename]
        path = os.path.join("assets", filename)
        if not os.path.exists(path): return None
        try:
            s = pygame.mixer.Sound(path)
            self.sounds[filename] = s
            return s
        except Exception: return None

    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = f"{size}_{bold}"
        if key not in self.fonts:
            # Preferencia por fuentes modernas sans-serif si existen en el sistema
            fonts = ["segoeui", "verdana", "arial", "sans"]
            font_obj = None
            try:
                font_obj = pygame.font.SysFont(fonts[0], size, bold=bold)
            except:
                font_obj = pygame.font.Font(None, size)
            self.fonts[key] = font_obj
        return self.fonts[key]

class Particle:
    def __init__(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.x, self.y, self.text, self.color = x, y, text, color
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
        
        self.simulation_running = False
        self.simulation_paused = False

        # Area del panel
        self.panel_rect = pygame.Rect(cfg.SCREEN_WIDTH - cfg.PANEL_WIDTH, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT)

        # Botones Principales (Toolbar Superior)
        self.toolbar_buttons: Dict[str, pygame.Rect] = {}
        
        # Botones Configuración
        self.config_buttons: Dict[str, Dict[str, Any]] = {}
        self.config: Dict[str, int] = cfg.DEFAULT_POPULATION.copy()

        self.turn_progress = 0.0

        # Gestión partidas
        self.save_slots: List[Dict[str, Any]] = []
        self.selected_save_id: Optional[str] = None
        self.active_save_name: str = ""
        self.pending_delete_id: Optional[str] = None

        # Input texto
        self.text_input_active = False
        self.text_input_value: str = ""
        self.text_input_mode: Optional[str] = None
        self.text_input_target_id: Optional[str] = None
        self.save_ui_rects: Dict[str, Any] = {"input": None, "create_btn": None, "load_btn": None, "slots": {}}

        # Inicializar rectángulos
        self.recalculate_layout()

    def recalculate_layout(self):
        """Define la posición de los elementos fijos (Toolbar)"""
        p_x = self.panel_rect.x + 15
        p_w = cfg.PANEL_WIDTH - 30
        
        # Toolbar superior (Start | Pause | Stop | Save)
        btn_w = (p_w - 15) // 3 # 3 botones principales
        y = 60
        
        self.toolbar_buttons["start"] = pygame.Rect(p_x, y, p_w, 40) # Start ocupa todo si no corre
        
        # Si corre: [Pause] [Stop] [Save]
        self.toolbar_buttons["pause"] = pygame.Rect(p_x, y, btn_w, 40)
        self.toolbar_buttons["stop"] = pygame.Rect(p_x + btn_w + 5, y, btn_w, 40)
        self.toolbar_buttons["save"] = pygame.Rect(p_x + (btn_w + 5)*2, y, btn_w + 5, 40)

        # Config buttons se calculan dinámicamente en draw, pero inicializamos dict
        self.config_buttons = {}

    def initialize(self) -> bool:
        try:
            pygame.init()
            pygame.display.set_caption("Simulador Ecosistema v2.0")
            self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
            self.clock = pygame.time.Clock()
            pygame.mixer.init()
            self.load_assets()
            return True
        except Exception as e:
            print(f"Error init: {e}")
            return False

    def load_assets(self):
        self.assets.load_image("pez.png", (20, 20))
        self.assets.load_image("trucha.png", (35, 35))
        self.assets.load_image("tiburon.png", (45, 45))
        self.assets.load_image("alga.png", (14, 14))
        # Sonidos opcionales
        for s in ["comer_planta.mp3", "comer.mp3", "morir.mp3", "musica_fondo_mar.mp3"]:
            self.assets.load_sound(s)

    def set_save_slots(self, slots: List[Dict[str, Any]], selected_id: Optional[str] = None):
        self.save_slots = slots
        # Validar selección
        if selected_id and any(s["save_id"] == selected_id for s in slots):
            self.selected_save_id = selected_id
        elif self.selected_save_id and not any(s["save_id"] == self.selected_save_id for s in slots):
            self.selected_save_id = None
        self.pending_delete_id = None

    def set_active_save_name(self, name: str):
        self.active_save_name = name or ""

    # ----------------- EVENTOS ----------------- #

    def handle_events(self) -> Optional[Any]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "quit"

            # Input texto
            if event.type == pygame.KEYDOWN and self.text_input_active:
                if event.key == pygame.K_RETURN:
                    txt = self.text_input_value.strip()
                    mode = self.text_input_mode
                    tid = self.text_input_target_id
                    self._reset_input()
                    
                    if not txt: return None
                    if mode == "create": return {"type": "save_create", "name": txt}
                    if mode == "rename" and tid: return {"type": "save_rename", "save_id": tid, "new_name": txt}

                elif event.key == pygame.K_BACKSPACE:
                    self.text_input_value = self.text_input_value[:-1]
                elif event.key == pygame.K_ESCAPE:
                    self._reset_input()
                else:
                    if len(self.text_input_value) < 25 and event.unicode.isprintable():
                        self.text_input_value += event.unicode
                return None

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: return "quit"
                if event.key == pygame.K_SPACE and self.simulation_running: return "toggle_pause"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.handle_click(event.pos)
                if action: return action

        return None

    def _reset_input(self):
        self.text_input_active = False
        self.text_input_mode = None
        self.text_input_target_id = None
        self.pending_delete_id = None

    def handle_click(self, pos: Tuple[int, int]) -> Optional[Any]:
        if not self.panel_rect.collidepoint(pos):
            self._reset_input()
            return None

        # 1. Toolbar Superior
        if not self.simulation_running:
            if self.toolbar_buttons["start"].collidepoint(pos):
                return "start" if self.selected_save_id else None
        else:
            if self.toolbar_buttons["pause"].collidepoint(pos): return "toggle_pause"
            if self.toolbar_buttons["stop"].collidepoint(pos): return "stop"
            if self.toolbar_buttons["save"].collidepoint(pos):
                if self.selected_save_id: return {"type": "save_manual", "save_id": self.selected_save_id}

        # 2. Configuración (Solo si no corre)
        if not self.simulation_running:
            for key, btns in self.config_buttons.items():
                if btns["minus"].collidepoint(pos):
                    self.config[key] = max(0, self.config[key] - 1)
                    return "config_changed"
                if btns["plus"].collidepoint(pos):
                    self.config[key] = min(cfg.POPULATION_LIMITS[key]["max"], self.config[key] + 1)
                    return "config_changed"

        # 3. Gestión Partidas (Input/Crear/Cargar/Slots)
        # Input Create
        if self.save_ui_rects.get("input") and self.save_ui_rects["input"].collidepoint(pos):
            self.text_input_mode = "create"
            self.text_input_active = True
            self.text_input_value = ""
            return None
            
        # Btn Crear
        if self.save_ui_rects.get("create_btn") and self.save_ui_rects["create_btn"].collidepoint(pos):
            txt = self.text_input_value.strip()
            self._reset_input()
            if txt: return {"type": "save_create", "name": txt}
            return None

        # Btn Cargar
        if self.save_ui_rects.get("load_btn") and self.save_ui_rects["load_btn"].collidepoint(pos):
            if self.selected_save_id: return {"type": "save_load", "save_id": self.selected_save_id}

        # Slots individuales
        slots_rects = self.save_ui_rects.get("slots", {})
        for save_id, rects in slots_rects.items():
            if rects["rename"].collidepoint(pos):
                slot = next((s for s in self.save_slots if s["save_id"] == save_id), None)
                if slot:
                    self.text_input_mode = "rename"
                    self.text_input_target_id = save_id
                    self.text_input_value = slot["save_name"]
                    self.text_input_active = True
                return None
            
            if rects["delete"].collidepoint(pos):
                if self.pending_delete_id == save_id:
                    self._reset_input()
                    return {"type": "save_delete", "save_id": save_id}
                else:
                    self.pending_delete_id = save_id
                    return None

            if rects["row"].collidepoint(pos):
                self.selected_save_id = save_id
                self._reset_input()
                return {"type": "save_select", "save_id": save_id}

        return None

    # ----------------- LOGICA VISUAL ----------------- #

    def update_particles(self):
        self.particles = [p for p in self.particles if not p.update()]

    def add_particle(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.particles.append(Particle(x, y, text, color))

    def process_ecosystem_events(self, events: List[Dict]):
        # Se mantiene igual para procesar eventos
        for event in events:
            if event["type"] == "eat":
                eater = event.get("eater", "")
                snd = self.assets.load_sound("comer_planta.mp3") if eater == "pez" else self.assets.load_sound("comer.mp3")
                self.add_particle(event["position"][0], event["position"][1], "+E", cfg.EAT_COLOR)
                if snd: snd.play()
            elif event["type"] == "birth":
                self.add_particle(event["position"][0], event["position"][1], "★", cfg.BIRTH_COLOR)
            elif event["type"] == "death":
                self.add_particle(event["position"][0], event["position"][1], "†", cfg.DEATH_COLOR)
                if self.assets.load_sound("morir.mp3"): self.assets.load_sound("morir.mp3").play()

    # ----------------- RENDERIZADO ----------------- #

    def render(self, ecosystem: Ecosystem):
        self.screen.fill(cfg.UI_BLACK) # Fondo seguro
        
        # 1. Dibujar Juego
        self.draw_game_area(ecosystem)
        self.draw_particles()
        
        # 2. Dibujar Panel UI
        self.draw_panel(ecosystem)
        
        # 3. Overlays
        if self.simulation_paused: self.draw_pause_overlay()
        
        pygame.display.flip()
        self.clock.tick(cfg.FPS)

    def draw_particles(self):
        # Usamos una fuente para efectos, por ejemplo tamaño 14 bold
        font = self.assets.get_font(14, True)
        for p in self.particles:
            p.draw(self.screen, font)

    def draw_game_area(self, ecosystem: Ecosystem):
        # Fondo degradado simple o solido
        rect = pygame.Rect(0, 0, cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, cfg.WATER_DARK, rect)
        
        # Grid/Lineas sutiles (Opcional, hace que se vea pro)
        # for y in range(0, cfg.SCREEN_HEIGHT, 40):
        #     pygame.draw.line(self.screen, (0, 80, 120), (0, y), (cfg.GAME_AREA_WIDTH, y))

        # Entidades
        all_entities = ecosystem.plants + ecosystem.fish + ecosystem.trout + ecosystem.sharks
        all_entities.sort(key=lambda e: e.y) # Z-index simple

        for e in all_entities:
            img_name = "alga.png" if isinstance(e, Plant) else \
                       "pez.png" if isinstance(e, Fish) else \
                       "trucha.png" if isinstance(e, Trout) else "tiburon.png"
            
            # Color fallback
            c = cfg.COLOR_PLANT if isinstance(e, Plant) else \
                cfg.COLOR_FISH if isinstance(e, Fish) else \
                cfg.COLOR_TROUT if isinstance(e, Trout) else cfg.COLOR_SHARK

            self.draw_entity(e, img_name, c)

        # Nombre partida (Flotante top-left)
        if self.active_save_name:
            f = self.assets.get_font(16, True)
            t = f.render(self.active_save_name, True, (255,255,255))
            bg = pygame.Surface((t.get_width()+10, t.get_height()+6))
            bg.fill((0,0,0))
            bg.set_alpha(100)
            self.screen.blit(bg, (10, 10))
            self.screen.blit(t, (15, 13))

    def draw_entity(self, entity, img_name, color):
        if entity.x > cfg.GAME_AREA_WIDTH: return
        img = self.assets.load_image(img_name)
        if img:
            if hasattr(entity, "direction") and entity.direction == -1:
                img = pygame.transform.flip(img, True, False)
            self.screen.blit(img, (int(entity.x), int(entity.y)))
        else:
            pygame.draw.circle(self.screen, color, (int(entity.x + entity.width/2), int(entity.y + entity.height/2)), entity.width//2)

    def draw_panel(self, ecosystem: Ecosystem):
        # Fondo Panel
        pygame.draw.rect(self.screen, cfg.UI_BG, self.panel_rect)
        pygame.draw.line(self.screen, cfg.UI_BORDER, (self.panel_rect.x, 0), (self.panel_rect.x, cfg.SCREEN_HEIGHT), 2)

        x_start = self.panel_rect.x + 15
        width = cfg.PANEL_WIDTH - 30
        curr_y = 20

        # TITULO
        title = self.assets.get_font(22, True).render("SIMULADOR BENYI", True, cfg.TEXT_ACCENT)
        self.screen.blit(title, (x_start, curr_y))
        
        # Subtítulo (Estado)
        status = "En ejecución" if self.simulation_running and not self.simulation_paused else \
                 "Pausado" if self.simulation_paused else "Detenido"
        st_surf = self.assets.get_font(14).render(status, True, cfg.TEXT_DIM)
        self.screen.blit(st_surf, (self.panel_rect.right - st_surf.get_width() - 15, curr_y + 5))
        
        curr_y += 40

        # TOOLBAR (Botones fijos)
        self.draw_toolbar(curr_y)
        curr_y += 50

        # CONTENIDO DINAMICO (Depende del estado)
        if self.simulation_running:
            # 1. Estadísticas (Card)
            curr_y = self.draw_section_stats(ecosystem, x_start, curr_y, width)
        else:
            # 1. Configuración (Card)
            curr_y = self.draw_section_config(x_start, curr_y, width)
            # 2. Guardado (Card)
            curr_y = self.draw_section_saves(x_start, curr_y, width)

    def draw_toolbar(self, y_pos):
        font = self.assets.get_font(16, True)
        
        if not self.simulation_running:
            # Boton START Grande
            rect = self.toolbar_buttons["start"]
            enabled = self.selected_save_id is not None
            self.draw_button_modern(rect, "COMENZAR SIMULACIÓN", cfg.BTN_PRIMARY, enabled, font)
        else:
            # Botones Pequeños
            # Pause
            p_txt = "REANUDAR" if self.simulation_paused else "PAUSAR"
            self.draw_button_modern(self.toolbar_buttons["pause"], p_txt, cfg.BTN_WARNING, True, self.assets.get_font(12, True))
            # Stop
            self.draw_button_modern(self.toolbar_buttons["stop"], "DETENER", cfg.BTN_DANGER, True, self.assets.get_font(12, True))
            # Save
            self.draw_button_modern(self.toolbar_buttons["save"], "GUARDAR", cfg.BTN_SUCCESS, True, self.assets.get_font(12, True))

    # --- SECCIONES (CARDS) ---

    def draw_card_bg(self, x, y, w, h, title=""):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, cfg.UI_CARD_BG, rect, border_radius=8)
        # pygame.draw.rect(self.screen, cfg.UI_BORDER, rect, 1, border_radius=8)
        if title:
            f = self.assets.get_font(14, True)
            t = f.render(title.upper(), True, cfg.TEXT_SEC)
            self.screen.blit(t, (x + 10, y + 10))
        return rect

    def draw_section_stats(self, ecosystem: Ecosystem, x, y, w) -> int:
        h = 280
        self.draw_card_bg(x, y, w, h, "Estadísticas en Tiempo Real")
        
        inner_y = y + 40
        padding = 15
        
        stats = ecosystem.get_statistics()
        
        # Barras de Población
        items = [
            ("Algas", stats["plants"], cfg.POPULATION_LIMITS["plantas"]["max"], cfg.COLOR_PLANT),
            ("Peces", stats["fish"], cfg.POPULATION_LIMITS["peces"]["max"], cfg.COLOR_FISH),
            ("Truchas", stats["trout"], cfg.POPULATION_LIMITS["truchas"]["max"], cfg.COLOR_TROUT),
            ("Tiburones", stats["sharks"], cfg.POPULATION_LIMITS["tiburones"]["max"], cfg.COLOR_SHARK),
        ]
        
        font_lbl = self.assets.get_font(13)
        font_num = self.assets.get_font(13, True)

        for label, val, max_val, color in items:
            # Label izquierda
            self.screen.blit(font_lbl.render(label, True, cfg.TEXT_MAIN), (x + padding, inner_y))
            # Numero derecha
            num_surf = font_num.render(str(val), True, cfg.TEXT_MAIN)
            self.screen.blit(num_surf, (x + w - padding - num_surf.get_width(), inner_y))
            inner_y += 18
            
            # Barra
            bar_w = w - (padding * 2)
            pygame.draw.rect(self.screen, cfg.BAR_BG, (x+padding, inner_y, bar_w, 6), border_radius=3)
            pct = val / max(1, max_val)
            if pct > 0:
                pygame.draw.rect(self.screen, color, (x+padding, inner_y, int(bar_w * min(1, pct)), 6), border_radius=3)
            inner_y += 15

        # Separador
        pygame.draw.line(self.screen, cfg.UI_BORDER, (x+10, inner_y+5), (x+w-10, inner_y+5))
        inner_y += 15

        # Tiempo
        season_color = cfg.SEASONS_CONFIG.get(stats["season"], {}).get("color", cfg.WHITE)
        self.screen.blit(font_lbl.render(f"Día {stats['day']} - {stats['season']}", True, cfg.TEXT_MAIN), (x + padding, inner_y))
        inner_y += 20
        # Barra dia
        bar_w = w - (padding * 2)
        pygame.draw.rect(self.screen, cfg.BAR_BG, (x+padding, inner_y, bar_w, 4), border_radius=2)
        pygame.draw.rect(self.screen, season_color, (x+padding, inner_y, int(bar_w * stats["season_progress"]), 4), border_radius=2)
        
        inner_y += 15
        t_day = stats["time_of_day"].capitalize()
        self.screen.blit(font_lbl.render(f"Ciclo: {t_day}", True, cfg.TEXT_DIM), (x + padding, inner_y))

        return y + h + 15

    def draw_section_config(self, x, y, w) -> int:
        h = 190
        self.draw_card_bg(x, y, w, h, "Población Inicial")
        inner_y = y + 35
        padding = 10
        
        items = [
            ("plantas", "Algas", cfg.COLOR_PLANT),
            ("peces", "Peces", cfg.COLOR_FISH),
            ("truchas", "Truchas", cfg.COLOR_TROUT),
            ("tiburones", "Tiburones", cfg.COLOR_SHARK),
        ]
        
        f = self.assets.get_font(14)
        
        for key, label, col in items:
            # Fila
            row_rect = pygame.Rect(x + padding, inner_y, w - padding*2, 30)
            
            # Label con bullet de color
            pygame.draw.circle(self.screen, col, (row_rect.x + 8, row_rect.centery), 4)
            self.screen.blit(f.render(label, True, cfg.TEXT_MAIN), (row_rect.x + 20, row_rect.y + 6))
            
            # Controles [ - ] [ Val ] [ + ] alineados a la derecha
            btn_size = 24
            
            plus_rect = pygame.Rect(row_rect.right - btn_size, row_rect.y + 3, btn_size, btn_size)
            val_rect = pygame.Rect(plus_rect.left - 40, row_rect.y, 40, 30)
            minus_rect = pygame.Rect(val_rect.left - btn_size, row_rect.y + 3, btn_size, btn_size)
            
            self.config_buttons[key] = {"minus": minus_rect, "plus": plus_rect}
            
            # Draw -
            self.draw_mini_btn(minus_rect, "-", self.config[key] > 0)
            # Draw Val
            val_txt = f.render(str(self.config[key]), True, cfg.TEXT_MAIN)
            self.screen.blit(val_txt, val_txt.get_rect(center=val_rect.center))
            # Draw +
            self.draw_mini_btn(plus_rect, "+", self.config[key] < cfg.POPULATION_LIMITS[key]["max"])
            
            inner_y += 38

        return y + h + 15

    def draw_section_saves(self, x, y, w) -> int:
        # Calcular altura dinamica
        slots_h = max(100, len(self.save_slots) * 35 + 40)
        h = 100 + slots_h
        
        self.draw_card_bg(x, y, w, h, "Gestor de Partidas")
        inner_y = y + 40
        padding = 10
        
        # 1. Input + Crear
        input_w = w - padding*2 - 70
        input_rect = pygame.Rect(x+padding, inner_y, input_w, 30)
        create_rect = pygame.Rect(input_rect.right + 5, inner_y, 65, 30)
        
        self.save_ui_rects["input"] = input_rect
        self.save_ui_rects["create_btn"] = create_rect
        
        # Draw Input
        pygame.draw.rect(self.screen, cfg.UI_BG, input_rect, border_radius=4)
        pygame.draw.rect(self.screen, cfg.UI_BORDER, input_rect, 1, border_radius=4)
        
        txt_show = self.text_input_value if (self.text_input_active and self.text_input_mode!="rename") else ""
        ph = "Nueva partida..." if not txt_show else txt_show
        col = cfg.TEXT_MAIN if txt_show else cfg.TEXT_DIM
        
        f = self.assets.get_font(13)
        self.screen.blit(f.render(ph, True, col), (input_rect.x + 8, input_rect.y + 7))
        
        # Draw Create
        self.draw_button_modern(create_rect, "Crear", cfg.BTN_PRIMARY, True, self.assets.get_font(12, True))
        
        inner_y += 45
        
        # 2. Lista
        self.save_ui_rects["slots"] = {}
        row_h = 30
        
        f_slot = self.assets.get_font(13)
        
        for slot in self.save_slots:
            sid = slot["save_id"]
            sname = slot["save_name"]
            
            row_rect = pygame.Rect(x+padding, inner_y, w - padding*2, row_h)
            
            is_sel = self.selected_save_id == sid
            bg_col = cfg.UI_BG if not is_sel else cfg.BTN_PRIMARY
            txt_col = cfg.TEXT_DIM if not is_sel else cfg.WHITE
            
            pygame.draw.rect(self.screen, bg_col, row_rect, border_radius=4)
            
            # Nombre
            trunc_name = (sname[:18] + '..') if len(sname) > 18 else sname
            self.screen.blit(f_slot.render(trunc_name, True, txt_col), (row_rect.x + 8, row_rect.y + 7))
            
            # Botones Accion (Rename / Delete)
            del_rect = pygame.Rect(row_rect.right - 25, row_rect.y + 3, 22, 24)
            ren_rect = pygame.Rect(del_rect.left - 25, row_rect.y + 3, 22, 24)
            
            # Logica UI Delete confirm
            del_col = cfg.BTN_NEUTRAL
            del_txt = "x"
            if self.pending_delete_id == sid:
                del_col = cfg.BTN_DANGER
                del_txt = "?"
            
            pygame.draw.rect(self.screen, cfg.BTN_NEUTRAL, ren_rect, border_radius=3)
            ren_s = f_slot.render("r", True, cfg.WHITE)
            self.screen.blit(ren_s, ren_s.get_rect(center=ren_rect.center))
            
            pygame.draw.rect(self.screen, del_col, del_rect, border_radius=3)
            del_s = f_slot.render(del_txt, True, cfg.WHITE)
            self.screen.blit(del_s, del_s.get_rect(center=del_rect.center))
            
            self.save_ui_rects["slots"][sid] = {"row": row_rect, "rename": ren_rect, "delete": del_rect}
            
            inner_y += 34
            
        # 3. Cargar
        inner_y += 10
        load_rect = pygame.Rect(x+padding, inner_y, w - padding*2, 35)
        self.save_ui_rects["load_btn"] = load_rect
        self.draw_button_modern(load_rect, "CARGAR PARTIDA SELECCIONADA", cfg.BTN_SUCCESS, self.selected_save_id is not None, self.assets.get_font(12, True))
        
        return inner_y + 40

    # --- COMPONENTES UI GENERICOS ---

    def draw_button_modern(self, rect, text, color, enabled, font):
        draw_col = color if enabled else cfg.BTN_NEUTRAL
        if enabled and rect.collidepoint(pygame.mouse.get_pos()):
            # Hover effect: slightly brighter
            draw_col = (min(255, draw_col.r + 20), min(255, draw_col.g + 20), min(255, draw_col.b + 20))
        
        pygame.draw.rect(self.screen, draw_col, rect, border_radius=5)
        
        txt_col = cfg.TEXT_MAIN if enabled else cfg.TEXT_DIM
        surf = font.render(text, True, txt_col)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_mini_btn(self, rect, text, enabled):
        col = cfg.BTN_NEUTRAL if enabled else cfg.UI_BG
        pygame.draw.rect(self.screen, col, rect, border_radius=4)
        f = self.assets.get_font(16, True)
        c = cfg.TEXT_MAIN if enabled else cfg.TEXT_DIM
        s = f.render(text, True, c)
        self.screen.blit(s, s.get_rect(center=rect.center))

    def draw_pause_overlay(self):
        overlay = pygame.Surface((cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))
        
        # Etiqueta moderna de pausa
        font = self.assets.get_font(40, True)
        surf = font.render("PAUSA", True, cfg.WHITE)
        bg = pygame.Rect(0, 0, surf.get_width() + 60, surf.get_height() + 40)
        bg.center = (cfg.GAME_AREA_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
        
        pygame.draw.rect(self.screen, cfg.UI_BG, bg, border_radius=15)
        pygame.draw.rect(self.screen, cfg.BTN_WARNING, bg, 2, border_radius=15)
        self.screen.blit(surf, surf.get_rect(center=bg.center))

    def cleanup(self):
        pygame.mixer.quit()
        pygame.quit()
    
    # Helpers que el controlador espera (API Legacy)
    def set_turn_progress(self, progress: float): self.turn_progress = progress
    def set_simulation_state(self, running: bool, paused: bool): self.simulation_running, self.simulation_paused = running, paused
    def get_configuration(self) -> Dict[str, int]: return self.config.copy()