"""
Sistema de visualización del juego.
Interfaz Gráfica con ViewModel para desacoplamiento.
"""

import os
import pygame
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass # Recomendado para DTOs de vista
import config as cfg
from game_logic import Ecosystem, Plant, Fish, Trout, Shark

# --- VIEW MODEL (Contrato de datos para la Vista) ---
@dataclass
class SaveSlotViewModel:
    id: str
    name: str
    display_info: str 

class AssetLoader:
    # (El contenido de AssetLoader se mantiene igual que tu original...)
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
        except: return None

    def load_sound(self, filename: str) -> Optional[pygame.mixer.Sound]:
        if filename in self.sounds: return self.sounds[filename]
        path = os.path.join("assets", filename)
        if not os.path.exists(path): return None
        try:
            s = pygame.mixer.Sound(path)
            self.sounds[filename] = s
            return s
        except: return None

    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = f"{size}_{bold}"
        if key not in self.fonts:
            try: self.fonts[key] = pygame.font.SysFont("segoeui", size, bold=bold)
            except: self.fonts[key] = pygame.font.Font(None, size)
        return self.fonts[key]

# (La clase Particle se mantiene igual...)
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

        self.panel_rect = pygame.Rect(cfg.SCREEN_WIDTH - cfg.PANEL_WIDTH, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT)
        self.toolbar_buttons: Dict[str, pygame.Rect] = {}
        self.config_buttons: Dict[str, Dict[str, Any]] = {}
        self.config: Dict[str, int] = cfg.DEFAULT_POPULATION.copy()
        self.turn_progress = 0.0

        # Gestión partidas usando VIEWMODEL
        self.save_slots: List[SaveSlotViewModel] = [] # Tipo estricto
        self.selected_save_id: Optional[str] = None
        self.active_save_name: str = ""
        self.pending_delete_id: Optional[str] = None

        self.text_input_active = False
        self.text_input_value: str = ""
        self.text_input_mode: Optional[str] = None
        self.text_input_target_id: Optional[str] = None
        self.save_ui_rects: Dict[str, Any] = {"input": None, "create_btn": None, "load_btn": None, "slots": {}}

        self.auto_save_enabled: bool = False
        self.auto_save_days: int = 30
        self.auto_save_rects: Dict[str, Optional[pygame.Rect]] = {"toggle": None, "minus": None, "plus": None}
        self.auto_save_feedback: str = ""
        self.auto_save_feedback_timer: float = 0.0

        self.recalculate_layout()

    # (Métodos de layout e initialize se mantienen igual...)
    def recalculate_layout(self):
        p_x = self.panel_rect.x + 15
        p_w = cfg.PANEL_WIDTH - 30
        btn_w = (p_w - 15) // 3
        y = 60
        self.toolbar_buttons["start"] = pygame.Rect(p_x, y, p_w, 40)
        self.toolbar_buttons["pause"] = pygame.Rect(p_x, y, btn_w, 40)
        self.toolbar_buttons["stop"] = pygame.Rect(p_x + btn_w + 5, y, btn_w, 40)
        self.toolbar_buttons["save"] = pygame.Rect(p_x + (btn_w + 5) * 2, y, btn_w + 5, 40)
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
        for s in ["comer_planta.mp3", "comer.mp3", "morir.mp3", "musica_fondo_mar.mp3"]:
            self.assets.load_sound(s)

    # --- CAMBIO IMPORTANTE: Recibe ViewModel, no Dict crudo ---
    def update_save_slots(self, slots: List[SaveSlotViewModel], selected_id: Optional[str] = None):
        self.save_slots = slots
        if selected_id and any(s.id == selected_id for s in slots):
            self.selected_save_id = selected_id
        elif self.selected_save_id and not any(s.id == self.selected_save_id for s in slots):
            self.selected_save_id = None
        self.pending_delete_id = None

    def set_active_save_name(self, name: str):
        self.active_save_name = name or ""

    def set_auto_save_feedback(self, message: str, duration: float = 2.5):
        self.auto_save_feedback = message
        self.auto_save_feedback_timer = max(0.0, float(duration))

    # (Handle events y lógica visual se mantienen igual, solo ajustando accesos a slots...)
    def handle_events(self) -> Optional[Any]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "quit"
            
            if event.type == pygame.KEYDOWN and self.text_input_active:
                if event.key == pygame.K_RETURN:
                    txt = self.text_input_value.strip()
                    mode, tid = self.text_input_mode, self.text_input_target_id
                    self._reset_input()
                    if not txt: return None
                    if mode == "create": return {"type": "save_create", "name": txt}
                    if mode == "rename" and tid: return {"type": "save_rename", "save_id": tid, "new_name": txt}
                elif event.key == pygame.K_BACKSPACE: self.text_input_value = self.text_input_value[:-1]
                elif event.key == pygame.K_ESCAPE: self._reset_input()
                else: 
                    if len(self.text_input_value) < 25 and event.unicode.isprintable(): self.text_input_value += event.unicode
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

        # Toolbar y Autosave (Sin cambios lógicos mayores)
        if not self.simulation_running:
            if self.toolbar_buttons["start"].collidepoint(pos): return "start" if self.selected_save_id else None
        else:
            if self.toolbar_buttons["pause"].collidepoint(pos): return "toggle_pause"
            if self.toolbar_buttons["stop"].collidepoint(pos): return "stop"
            if self.toolbar_buttons["save"].collidepoint(pos):
                if self.selected_save_id: return {"type": "save_manual", "save_id": self.selected_save_id}

        toggle_rect = self.auto_save_rects.get("toggle")
        if toggle_rect and toggle_rect.collidepoint(pos):
            self.auto_save_enabled = not self.auto_save_enabled
            return {"type": "auto_save_toggle", "enabled": self.auto_save_enabled}

        if self.auto_save_enabled:
            minus, plus = self.auto_save_rects.get("minus"), self.auto_save_rects.get("plus")
            if minus and minus.collidepoint(pos):
                self.auto_save_days = max(1, self.auto_save_days - 1)
                return {"type": "auto_save_update_interval", "days": self.auto_save_days}
            if plus and plus.collidepoint(pos):
                self.auto_save_days = min(365, self.auto_save_days + 1)
                return {"type": "auto_save_update_interval", "days": self.auto_save_days}

        if not self.simulation_running:
            for key, btns in self.config_buttons.items():
                if btns["minus"].collidepoint(pos):
                    self.config[key] = max(0, self.config[key] - 1)
                    return "config_changed"
                if btns["plus"].collidepoint(pos):
                    self.config[key] = min(cfg.POPULATION_LIMITS[key]["max"], self.config[key] + 1)
                    return "config_changed"

        # Slots logic usando ViewModel
        if self.save_ui_rects.get("input") and self.save_ui_rects["input"].collidepoint(pos):
            self.text_input_mode = "create"
            self.text_input_active = True
            self.text_input_value = ""
            return None

        if self.save_ui_rects.get("create_btn") and self.save_ui_rects["create_btn"].collidepoint(pos):
            txt = self.text_input_value.strip()
            self._reset_input()
            return {"type": "save_create", "name": txt} if txt else None

        if self.save_ui_rects.get("load_btn") and self.save_ui_rects["load_btn"].collidepoint(pos):
            if self.selected_save_id: return {"type": "save_load", "save_id": self.selected_save_id}

        slots_rects = self.save_ui_rects.get("slots", {})
        for save_id, rects in slots_rects.items():
            if rects["rename"].collidepoint(pos):
                # Buscamos en la lista de ViewModels
                slot = next((s for s in self.save_slots if s.id == save_id), None)
                if slot:
                    self.text_input_mode = "rename"
                    self.text_input_target_id = save_id
                    self.text_input_value = slot.name
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

    # (Particle update y process events se mantienen igual...)
    def update_particles(self, delta_time: float):
        self.particles = [p for p in self.particles if not p.update()]
        if self.auto_save_feedback_timer > 0:
            self.auto_save_feedback_timer -= delta_time
            if self.auto_save_feedback_timer <= 0:
                self.auto_save_feedback_timer = 0.0
                self.auto_save_feedback = ""

    def add_particle(self, x: float, y: float, text: str, color: Tuple[int, int, int]):
        self.particles.append(Particle(x, y, text, color))

    def process_ecosystem_events(self, events: List[Dict]):
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
                snd = self.assets.load_sound("morir.mp3")
                if snd: snd.play()

    # (Render y Draws sin cambios mayores, salvo el acceso a save_slots)
    def render(self, ecosystem: Ecosystem):
        self.screen.fill(cfg.UI_BLACK)
        self.draw_game_area(ecosystem)
        self.draw_particles()
        self.draw_panel(ecosystem)
        if self.simulation_paused: self.draw_pause_overlay()
        pygame.display.flip()
        self.clock.tick(cfg.FPS)

    def draw_particles(self):
        font = self.assets.get_font(14, True)
        for p in self.particles: p.draw(self.screen, font)

    def draw_game_area(self, ecosystem: Ecosystem):
        rect = pygame.Rect(0, 0, cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, cfg.WATER_DARK, rect)
        
        # Renderizado de Entidades (Optimizado)
        all_entities = ecosystem.plants + ecosystem.fish + ecosystem.trout + ecosystem.sharks
        all_entities.sort(key=lambda e: e.y)
        
        for e in all_entities:
            img_name = "alga.png" if isinstance(e, Plant) else "pez.png" if isinstance(e, Fish) else "trucha.png" if isinstance(e, Trout) else "tiburon.png"
            c = cfg.COLOR_PLANT if isinstance(e, Plant) else cfg.COLOR_FISH if isinstance(e, Fish) else cfg.COLOR_TROUT if isinstance(e, Trout) else cfg.COLOR_SHARK
            if e.x <= cfg.GAME_AREA_WIDTH:
                img = self.assets.load_image(img_name)
                if img:
                    if hasattr(e, "direction") and e.direction == -1: img = pygame.transform.flip(img, True, False)
                    self.screen.blit(img, (int(e.x), int(e.y)))
                else:
                    pygame.draw.circle(self.screen, c, (int(e.x + e.width / 2), int(e.y + e.height / 2)), e.width // 2)

        if self.active_save_name:
            f = self.assets.get_font(16, True)
            t = f.render(self.active_save_name, True, (255, 255, 255))
            bg = pygame.Surface((t.get_width() + 10, t.get_height() + 6))
            bg.fill((0, 0, 0))
            bg.set_alpha(100)
            self.screen.blit(bg, (10, 10))
            self.screen.blit(t, (15, 13))

    def draw_panel(self, ecosystem: Ecosystem):
        pygame.draw.rect(self.screen, cfg.UI_BG, self.panel_rect)
        pygame.draw.line(self.screen, cfg.UI_BORDER, (self.panel_rect.x, 0), (self.panel_rect.x, cfg.SCREEN_HEIGHT), 2)
        
        x, width, curr_y = self.panel_rect.x + 15, cfg.PANEL_WIDTH - 30, 20
        title = self.assets.get_font(22, True).render("SIMULADOR BENYI", True, cfg.TEXT_ACCENT)
        self.screen.blit(title, (x, curr_y))
        
        status = "En ejecución" if self.simulation_running and not self.simulation_paused else "Pausado" if self.simulation_paused else "Detenido"
        st_surf = self.assets.get_font(14).render(status, True, cfg.TEXT_DIM)
        self.screen.blit(st_surf, (self.panel_rect.right - st_surf.get_width() - 15, curr_y + 5))
        
        curr_y += 40
        self.draw_toolbar(curr_y)
        curr_y += 50
        curr_y = self.draw_section_autosave(x, curr_y, width)

        if self.simulation_running:
            curr_y = self.draw_section_stats(ecosystem, x, curr_y, width)
        else:
            curr_y = self.draw_section_config(x, curr_y, width)
            curr_y = self.draw_section_saves(x, curr_y, width)

        if self.auto_save_feedback:
            f_msg = self.assets.get_font(12)
            msg_surf = f_msg.render(self.auto_save_feedback, True, cfg.TEXT_ACCENT)
            bg = pygame.Surface((msg_surf.get_width() + 14, msg_surf.get_height() + 8), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            x_f, y_f = self.panel_rect.x + 15, cfg.SCREEN_HEIGHT - bg.get_height() - 15
            self.screen.blit(bg, (x_f, y_f))
            self.screen.blit(msg_surf, (x_f + 7, y_f + 4))

    def draw_toolbar(self, y_pos):
        if not self.simulation_running:
            enabled = self.selected_save_id is not None
            self.draw_button_modern(self.toolbar_buttons["start"], "COMENZAR SIMULACIÓN", cfg.BTN_PRIMARY, enabled, self.assets.get_font(16, True))
        else:
            p_txt = "REANUDAR" if self.simulation_paused else "PAUSAR"
            self.draw_button_modern(self.toolbar_buttons["pause"], p_txt, cfg.BTN_WARNING, True, self.assets.get_font(12, True))
            self.draw_button_modern(self.toolbar_buttons["stop"], "DETENER", cfg.BTN_DANGER, True, self.assets.get_font(12, True))
            self.draw_button_modern(self.toolbar_buttons["save"], "GUARDAR", cfg.BTN_SUCCESS, True, self.assets.get_font(12, True))

    def draw_card_bg(self, x, y, w, h, title=""):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(self.screen, cfg.UI_CARD_BG, rect, border_radius=8)
        if title:
            t = self.assets.get_font(14, True).render(title.upper(), True, cfg.TEXT_SEC)
            self.screen.blit(t, (x + 10, y + 10))
        return rect

    def draw_section_autosave(self, x, y, w) -> int:
        h = 60 if not self.auto_save_enabled else 100
        self.draw_card_bg(x, y, w, h, "Autoguardado")
        inner_y = y + 36
        padding = 10
        
        toggle_rect = pygame.Rect(x + padding, inner_y, 110, 28)
        self.auto_save_rects["toggle"] = toggle_rect
        label, col = ("AUTO: ON", cfg.BTN_SUCCESS) if self.auto_save_enabled else ("AUTO: OFF", cfg.BTN_NEUTRAL)
        self.draw_button_modern(toggle_rect, label, col, True, self.assets.get_font(12, True))
        
        info_surf = self.assets.get_font(11).render("Guarda solo mientras la simulación está en marcha.", True, cfg.TEXT_DIM)
        self.screen.blit(info_surf, (x + padding + 120, inner_y + 6))
        
        self.auto_save_rects["minus"] = self.auto_save_rects["plus"] = None
        if self.auto_save_enabled:
            inner_y += 32
            self.screen.blit(self.assets.get_font(12).render("Guardar cada (días):", True, cfg.TEXT_MAIN), (x + padding, inner_y + 4))
            btn_size = 22
            minus = pygame.Rect(x + padding + 135, inner_y, btn_size, btn_size)
            val = pygame.Rect(minus.right + 4, inner_y, 40, btn_size)
            plus = pygame.Rect(val.right + 4, inner_y, btn_size, btn_size)
            self.auto_save_rects["minus"], self.auto_save_rects["plus"] = minus, plus
            
            self.draw_mini_btn(minus, "-", True)
            val_s = self.assets.get_font(12).render(str(self.auto_save_days), True, cfg.TEXT_MAIN)
            pygame.draw.rect(self.screen, cfg.UI_BG, val, border_radius=4)
            pygame.draw.rect(self.screen, cfg.UI_BORDER, val, 1, border_radius=4)
            self.screen.blit(val_s, val_s.get_rect(center=val.center))
            self.draw_mini_btn(plus, "+", True)
        return y + h + 15

    def draw_section_stats(self, ecosystem: Ecosystem, x, y, w) -> int:
        h = 280
        self.draw_card_bg(x, y, w, h, "Estadísticas en Tiempo Real")
        inner_y, padding = y + 40, 15
        stats = ecosystem.get_statistics()
        items = [("Algas", stats["plants"], cfg.POPULATION_LIMITS["plantas"]["max"], cfg.COLOR_PLANT),
                 ("Peces", stats["fish"], cfg.POPULATION_LIMITS["peces"]["max"], cfg.COLOR_FISH),
                 ("Truchas", stats["trout"], cfg.POPULATION_LIMITS["truchas"]["max"], cfg.COLOR_TROUT),
                 ("Tiburones", stats["sharks"], cfg.POPULATION_LIMITS["tiburones"]["max"], cfg.COLOR_SHARK)]
        
        font_lbl, font_num = self.assets.get_font(13), self.assets.get_font(13, True)
        for lbl, val, mx, col in items:
            self.screen.blit(font_lbl.render(lbl, True, cfg.TEXT_MAIN), (x + padding, inner_y))
            num = font_num.render(str(val), True, cfg.TEXT_MAIN)
            self.screen.blit(num, (x + w - padding - num.get_width(), inner_y))
            inner_y += 18
            bar_w = w - padding * 2
            pygame.draw.rect(self.screen, cfg.BAR_BG, (x + padding, inner_y, bar_w, 6), border_radius=3)
            pct = val / max(1, mx)
            if pct > 0: pygame.draw.rect(self.screen, col, (x + padding, inner_y, int(bar_w * min(1, pct)), 6), border_radius=3)
            inner_y += 15
            
        pygame.draw.line(self.screen, cfg.UI_BORDER, (x + 10, inner_y + 5), (x + w - 10, inner_y + 5))
        inner_y += 15
        
        sc = cfg.SEASONS_CONFIG.get(stats["season"], {}).get("color", cfg.WHITE)
        self.screen.blit(font_lbl.render(f"Día {stats['day']} - {stats['season']}", True, cfg.TEXT_MAIN), (x + padding, inner_y))
        inner_y += 20
        pygame.draw.rect(self.screen, cfg.BAR_BG, (x + padding, inner_y, w - padding * 2, 4), border_radius=2)
        pygame.draw.rect(self.screen, sc, (x + padding, inner_y, int((w - padding * 2) * stats["season_progress"]), 4), border_radius=2)
        inner_y += 15
        self.screen.blit(font_lbl.render(f"Ciclo: {stats['time_of_day'].capitalize()}", True, cfg.TEXT_DIM), (x + padding, inner_y))
        return y + h + 15

    def draw_section_config(self, x, y, w) -> int:
        h = 190
        self.draw_card_bg(x, y, w, h, "Población Inicial")
        inner_y, padding = y + 35, 10
        items = [("plantas", "Algas", cfg.COLOR_PLANT), ("peces", "Peces", cfg.COLOR_FISH), ("truchas", "Truchas", cfg.COLOR_TROUT), ("tiburones", "Tiburones", cfg.COLOR_SHARK)]
        f = self.assets.get_font(14)
        for key, lbl, col in items:
            row = pygame.Rect(x + padding, inner_y, w - padding * 2, 30)
            pygame.draw.circle(self.screen, col, (row.x + 8, row.centery), 4)
            self.screen.blit(f.render(lbl, True, cfg.TEXT_MAIN), (row.x + 20, row.y + 6))
            btn_s = 24
            plus = pygame.Rect(row.right - btn_s, row.y + 3, btn_s, btn_s)
            val = pygame.Rect(plus.left - 40, row.y, 40, 30)
            minus = pygame.Rect(val.left - btn_s, row.y + 3, btn_s, btn_s)
            self.config_buttons[key] = {"minus": minus, "plus": plus}
            self.draw_mini_btn(minus, "-", self.config[key] > 0)
            vt = f.render(str(self.config[key]), True, cfg.TEXT_MAIN)
            self.screen.blit(vt, vt.get_rect(center=val.center))
            self.draw_mini_btn(plus, "+", self.config[key] < cfg.POPULATION_LIMITS[key]["max"])
            inner_y += 38
        return y + h + 15

    def draw_section_saves(self, x, y, w) -> int:
        slots_h = max(100, len(self.save_slots) * 35 + 40)
        h = 100 + slots_h
        self.draw_card_bg(x, y, w, h, "Gestor de Partidas")
        inner_y, padding = y + 40, 10
        
        in_w = w - padding * 2 - 70
        in_r = pygame.Rect(x + padding, inner_y, in_w, 30)
        cr_r = pygame.Rect(in_r.right + 5, inner_y, 65, 30)
        self.save_ui_rects["input"], self.save_ui_rects["create_btn"] = in_r, cr_r
        
        pygame.draw.rect(self.screen, cfg.UI_BG, in_r, border_radius=4)
        pygame.draw.rect(self.screen, cfg.UI_BORDER, in_r, 1, border_radius=4)
        ts = self.text_input_value if (self.text_input_active and self.text_input_mode != "rename") else ""
        ph, col = ("Nueva partida..." if not ts else ts, cfg.TEXT_DIM if not ts else cfg.TEXT_MAIN)
        self.screen.blit(self.assets.get_font(13).render(ph, True, col), (in_r.x + 8, in_r.y + 7))
        self.draw_button_modern(cr_r, "Crear", cfg.BTN_PRIMARY, True, self.assets.get_font(12, True))
        
        inner_y += 45
        self.save_ui_rects["slots"] = {}
        row_h, f_slot = 30, self.assets.get_font(13)
        
        for slot in self.save_slots:
            row_r = pygame.Rect(x + padding, inner_y, w - padding * 2, row_h)
            is_sel = self.selected_save_id == slot.id
            bg, tc = (cfg.BTN_PRIMARY, cfg.WHITE) if is_sel else (cfg.UI_BG, cfg.TEXT_DIM)
            pygame.draw.rect(self.screen, bg, row_r, border_radius=4)
            
            nm = slot.name
            trunc = (nm[:18] + "..") if len(nm) > 18 else nm
            self.screen.blit(f_slot.render(trunc, True, tc), (row_r.x + 8, row_r.y + 7))
            
            del_r = pygame.Rect(row_r.right - 25, row_r.y + 3, 22, 24)
            ren_r = pygame.Rect(del_r.left - 25, row_r.y + 3, 22, 24)
            
            del_col, del_txt = (cfg.BTN_DANGER, "?") if self.pending_delete_id == slot.id else (cfg.BTN_NEUTRAL, "x")
            
            pygame.draw.rect(self.screen, cfg.BTN_NEUTRAL, ren_r, border_radius=3)
            rs = f_slot.render("r", True, cfg.WHITE)
            self.screen.blit(rs, rs.get_rect(center=ren_r.center))
            
            pygame.draw.rect(self.screen, del_col, del_r, border_radius=3)
            ds = f_slot.render(del_txt, True, cfg.WHITE)
            self.screen.blit(ds, ds.get_rect(center=del_r.center))
            
            self.save_ui_rects["slots"][slot.id] = {"row": row_r, "rename": ren_r, "delete": del_r}
            inner_y += 34
            
        inner_y += 10
        load_r = pygame.Rect(x + padding, inner_y, w - padding * 2, 35)
        self.save_ui_rects["load_btn"] = load_r
        self.draw_button_modern(load_r, "CARGAR PARTIDA SELECCIONADA", cfg.BTN_SUCCESS, self.selected_save_id is not None, self.assets.get_font(12, True))
        return inner_y + 40

    def draw_button_modern(self, rect, text, color, enabled, font):
        draw_col = color if enabled else cfg.BTN_NEUTRAL
        if enabled and rect.collidepoint(pygame.mouse.get_pos()):
            draw_col = (min(255, draw_col.r + 20), min(255, draw_col.g + 20), min(255, draw_col.b + 20))
        pygame.draw.rect(self.screen, draw_col, rect, border_radius=5)
        surf = font.render(text, True, cfg.TEXT_MAIN if enabled else cfg.TEXT_DIM)
        self.screen.blit(surf, surf.get_rect(center=rect.center))

    def draw_mini_btn(self, rect, text, enabled):
        pygame.draw.rect(self.screen, cfg.BTN_NEUTRAL if enabled else cfg.UI_BG, rect, border_radius=4)
        s = self.assets.get_font(16, True).render(text, True, cfg.TEXT_MAIN if enabled else cfg.TEXT_DIM)
        self.screen.blit(s, s.get_rect(center=rect.center))

    def draw_pause_overlay(self):
        ov = pygame.Surface((cfg.GAME_AREA_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 100))
        self.screen.blit(ov, (0, 0))
        s = self.assets.get_font(40, True).render("PAUSA", True, cfg.WHITE)
        bg = pygame.Rect(0, 0, s.get_width() + 60, s.get_height() + 40)
        bg.center = (cfg.GAME_AREA_WIDTH // 2, cfg.SCREEN_HEIGHT // 2)
        pygame.draw.rect(self.screen, cfg.UI_BG, bg, border_radius=15)
        pygame.draw.rect(self.screen, cfg.BTN_WARNING, bg, 2, border_radius=15)
        self.screen.blit(s, s.get_rect(center=bg.center))

    def cleanup(self):
        pygame.mixer.quit()
        pygame.quit()
    
    def set_turn_progress(self, progress: float): self.turn_progress = progress
    def set_simulation_state(self, running: bool, paused: bool): self.simulation_running, self.simulation_paused = running, paused
    def get_configuration(self) -> Dict[str, int]: return self.config.copy()