import os
import pygame
import random
from logic import (
    BLANCO, AZUL, VERDE, MARRON, GRIS, 
    AGUA_CLARA, AGUA_OSCURA, NEGRO_UI,
    COLOR_TEXTO_BTN, COLOR_START, COLOR_STOP, COLOR_PAUSE, COLOR_RESUME,
    TEXTURAS, TEXTURAS_TAM,
    COLOR_COMER, COLOR_NACER, COLOR_MORIR,
    COLOR_BURBUJA,
    # Importar clases de entidades para isinstance
    Planta, Pez, Trucha, Tiburon,
    # Importar nuevos colores de UI
    Color, COLOR_PANEL_FONDO, COLOR_TEXTO_TITULO, COLOR_TEXTO_NORMAL,
    COLOR_BARRA_FONDO, COLOR_BARRA_PROGRESO, COLOR_SEPARADOR,
    WIDTH, HEIGHT # Importar dimensiones
)

# --- (IDEA 3) Clase para Efectos Visuales ---
class Particula:
    """Gestiona un texto flotante para eventos (comer, nacer, morir)."""
    def __init__(self, texto, pos, color, vida=45, velocidad_y=-0.5):
        self.x, self.y = pos
        self.texto = texto
        self.color = color
        self.vida_maxima = vida
        self.vida = vida
        self.velocidad_y = velocidad_y
        self.alpha = 255
        self.rect = pygame.Rect(self.x, self.y, 20, 20) 

    def actualizar(self):
        """Mueve la partícula hacia arriba y reduce su vida."""
        self.y += self.velocidad_y
        self.vida -= 1
        if self.vida < self.vida_maxima / 2:
            self.alpha = int(255 * (self.vida / (self.vida_maxima / 2)))
        self.alpha = max(0, min(255, self.alpha))
        self.rect.topleft = (int(self.x), int(self.y))

    def dibujar(self, screen, font, offset=(0,0)):
        """Dibuja el texto de la partícula."""
        try:
            img = font.render(self.texto, True, self.color)
            img.set_alpha(self.alpha)
            screen.blit(img, (int(self.x + offset[0]), int(self.y + offset[1])))
        except Exception as e:
            pass # Evitar crash si la fuente falla

# --- (IDEA 10) Clase para Burbujas ---
class Burbuja:
    """Una burbuja que sube y se desvanece."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vida_maxima = random.randint(60, 120)
        self.vida = self.vida_maxima
        self.velocidad_y = random.uniform(-1.0, -0.5)
        self.radio_max = random.randint(2, 5)
        self.radio = 1
        self.rect = pygame.Rect(self.x - self.radio, self.y - self.radio, self.radio*2, self.radio*2)

    def actualizar(self):
        """Mueve la burbuja hacia arriba y ajusta su radio."""
        self.y += self.velocidad_y
        self.vida -= 1
        if self.vida > self.vida_maxima - 10:
             self.radio = int(self.radio_max * ( (self.vida_maxima - self.vida) / 10.0) )
        elif self.vida < 20:
            self.radio = int(self.radio_max * (self.vida / 20.0))
        else:
            self.radio = self.radio_max
        self.radio = max(1, self.radio)
        self.rect.center = (int(self.x), int(self.y))
    
    def dibujar(self, screen, offset=(0,0)):
        """Dibuja la burbuja como un círculo semi-transparente."""
        if self.radio < 1:
            return
        try:
            # Dibuja directamente en la pantalla con transparencia
            surf = pygame.Surface((self.radio*2, self.radio*2), pygame.SRCALPHA)
            alpha = int(90 * (self.vida / self.vida_maxima)) 
            color_con_alpha = COLOR_BURBUJA + (alpha,)
            pygame.draw.circle(surf, color_con_alpha, (self.radio, self.radio), self.radio)
            
            # Aplicar offset y dibujar
            screen.blit(surf, (self.rect.x + offset[0], self.rect.y + offset[1]))
        except Exception:
            pass # Evitar crash si el radio es inválido

# --- Clase Vista Principal (Rediseñada) ---

class Vista:
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema Acuático")
        self.assets = self.cargar_assets_flexible()
        
        self.fondo_superficie = self._crear_fondo_estatico(width, height)
        
        # --- Carga de Fuentes ---
        try:
            self.font_titulo = pygame.font.SysFont('Arial', 24, bold=True)
            self.font_normal = pygame.font.SysFont('Arial', 18)
            self.font_pequeno = pygame.font.SysFont('Arial', 14)
            self.font_overlay = pygame.font.SysFont('Arial', 100, bold=True)
            self.font_particula = pygame.font.SysFont('Arial', 18, bold=True)
        except:
            print("Warning: No se pudo cargar la fuente. Usando fuentes por defecto.")
            # Fallback a fuentes por defecto
            self.font_titulo = pygame.font.SysFont(None, 30)
            self.font_normal = pygame.font.SysFont(None, 24)
            self.font_pequeno = pygame.font.SysFont(None, 18)
            self.font_overlay = pygame.font.SysFont(None, 100)
            self.font_particula = pygame.font.SysFont(None, 18)

        # --- Estado de Simulación ---
        self.sim_running = False
        self.sim_paused = False

        # --- Definición del Panel Lateral (UI) ---
        self.panel_ancho = 280
        self.panel_rect = pygame.Rect(self.width - self.panel_ancho, 0, self.panel_ancho, self.height)
        self.panel_padding = 20

        # --- Botones de Control (dentro del panel) ---
        px = self.panel_rect.x + self.panel_padding
        py = self.panel_padding + 40 # Espacio para el título
        btn_w = self.panel_ancho - (self.panel_padding * 2)
        btn_h = 40
        self.btn_start = pygame.Rect(px, py, btn_w, btn_h)
        self.btn_pause = pygame.Rect(px, py + btn_h + 10, btn_w, btn_h)
        self.btn_stop = pygame.Rect(px, py + (btn_h + 10) * 2, btn_w, btn_h)

        # --- Configuración Previa (dentro del panel) ---
        self.cfg = {
            'plantas': 25, 'peces': 15, 'truchas': 5, 'tiburones': 2,
        }
        self.cfg_rows = []
        base_y = self.btn_stop.bottom + 50 # Debajo de los botones
        
        # --- (Req 2) Actualizado para incluir asset_key y color ---
        cfg_data = [
            ('Algas', 'plantas', 'alga', VERDE), 
            ('Peces', 'peces', 'pez', AZUL), 
            ('Truchas', 'truchas', 'trucha', MARRON), 
            ('Tiburones', 'tiburones', 'tiburon', GRIS)
        ]
        
        px_controles = px + 100 # Donde empiezan los +/-
        
        for i, (label, key, asset_key, color) in enumerate(cfg_data):
            y = base_y + i * 40
            # Layout: [IMG] [Label]... [ - ] [ 5 ] [ + ]
            img_rect = pygame.Rect(px, y, 30, 30)
            lbl_rect = pygame.Rect(img_rect.right + 5, y, 90, 30)
            minus_rect = pygame.Rect(lbl_rect.right + 5, y, 30, 30)
            text_rect = pygame.Rect(minus_rect.right, y, 40, 30) # Más espacio para números
            plus_rect = pygame.Rect(text_rect.right, y, 30, 30)
            
            self.cfg_rows.append({
                'label': label, 'key': key, 'asset_key': asset_key, 'color': color,
                'img_rect': img_rect, 'lbl_rect': lbl_rect,
                'minus': minus_rect, 'plus': plus_rect, 'text_rect': text_rect
            })

        # --- Partículas y Efectos ---
        self.particulas = []
        self.burbujas = []
        self.screen_shake = 0
        
        # --- Almacén de Estadísticas (de main.py) ---
        self.turn_progress = 0.0
        self.sim_minutes = 0
        self.top_species = "N/A"
        self.scores = {}

    def _crear_fondo_estatico(self, width, height):
        fondo = pygame.Surface((width, height))
        for y in range(height):
            ratio = y / height
            r = int(AGUA_CLARA[0] * (1 - ratio) + AGUA_OSCURA[0] * ratio)
            g = int(AGUA_CLARA[1] * (1 - ratio) + AGUA_OSCURA[1] * ratio)
            b = int(AGUA_CLARA[2] * (1 - ratio) + AGUA_OSCURA[2] * ratio)
            color_interpolado = (r, g, b)
            pygame.draw.line(fondo, color_interpolado, (0, y), (width, y))
        return fondo

    def cargar_assets_flexible(self):
        assets = {}
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, 'assets')

        def try_load(names, size):
            for name in names:
                path = os.path.join(assets_dir, name)
                if os.path.isfile(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        return pygame.transform.scale(img, size)
                    except Exception as e:
                        print(f"Error cargando {path}: {e}")
            return None
        
        for key, names in TEXTURAS.items():
            size = TEXTURAS_TAM.get(key, (20, 20))
            img = try_load(names, size)
            if img:
                assets[key] = img
        
        if assets:
            print(f"Assets cargados: {list(assets.keys())} desde '{assets_dir}'.")
        else:
            print(f"Advertencia: no se cargó ninguna imagen desde '{assets_dir}'. Se usarán formas básicas.")
        return assets

    def _dibujar_boton(self, rect, color_base, texto, color_texto=COLOR_TEXTO_BTN, offset=(0,0), hover_color=None):
        """Dibuja un botón con offset y efecto hover opcional."""
        rect_con_offset = rect.move(offset)
        color = color_base
        
        # --- Efecto Hover (Idea 5) ---
        if hover_color and rect_con_offset.collidepoint(pygame.mouse.get_pos()):
            # Interpola el color (lerp)
            color = color_base.lerp(hover_color, 0.3)
            
        pygame.draw.rect(self.screen, color, rect_con_offset, border_radius=5)
        img_texto = self.font_normal.render(texto, True, color_texto)
        pos_texto = img_texto.get_rect(center=rect_con_offset.center)
        self.screen.blit(img_texto, pos_texto)

    def _dibujar_barra_progreso(self, rect, progress, color_fg, color_bg, offset=(0,0)):
        """Dibuja una barra de progreso con offset."""
        rect_con_offset = rect.move(offset)
        pygame.draw.rect(self.screen, color_bg, rect_con_offset, border_radius=4)
        progress = max(0, min(1, progress)) # Asegurar 0.0 a 1.0
        fg_rect = pygame.Rect(rect_con_offset.x, rect_con_offset.y, 
                              int(rect_con_offset.width * progress), rect_con_offset.height)
        pygame.draw.rect(self.screen, color_fg, fg_rect, border_radius=4)

    def dibujar_overlay_pausa(self, offset=(0,0)):
        """Dibuja el overlay de Pausa con offset."""
        if not self.font_overlay:
            return
        # El overlay cubre solo el área de simulación
        overlay_rect = pygame.Rect(0, 0, self.panel_rect.left, self.height)
        overlay = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0,0)) # Se dibuja en 0,0
        
        # El texto sí vibra
        img_pausa = self.font_overlay.render("PAUSA", True, BLANCO)
        # Centrar en el área de simulación
        pos_pausa = img_pausa.get_rect(center=(overlay_rect.centerx + offset[0], overlay_rect.centery + offset[1]))
        self.screen.blit(img_pausa, pos_pausa)

    # --- Bucle de Dibujo Principal ---

    def dibujar_ecosistema(self, ecosistema):
        
        shake_offset = (0, 0)
        if self.screen_shake > 0:
            self.screen_shake -= 1
            shake_offset = (random.randint(-4, 4), random.randint(-4, 4))
            
        # 1. Dibujar la simulación (fondo y entidades)
        self.screen.blit(self.fondo_superficie, shake_offset)
        
        # Actualizar y crear burbujas
        for i in range(len(self.burbujas) - 1, -1, -1):
            b = self.burbujas[i]
            b.actualizar()
            if b.vida <= 0:
                self.burbujas.pop(i)
        
        if self.sim_running and not self.sim_paused:
            plantas, peces, truchas, tiburones = ecosistema.get_all_entities()
            animales_que_respiran = peces + truchas
            if random.random() < 0.05: 
                if animales_que_respiran:
                    animal = random.choice(animales_que_respiran)
                    # No crear burbujas en la zona del panel
                    if animal.rect.centerx < self.panel_rect.left:
                        self.burbujas.append(Burbuja(animal.rect.centerx, animal.rect.top))
        else:
            plantas, peces, truchas, tiburones = [],[],[],[] # Vacío si no corre

        # Z-Sorting (Falso 3D)
        todas_las_entidades = (
            plantas + peces + truchas + tiburones + self.burbujas
        )
        todas_las_entidades.sort(key=lambda e: e.rect.bottom)
        
        for entidad in todas_las_entidades:
            # No dibujar entidades que estén "detrás" del panel
            if entidad.rect.right > self.panel_rect.left:
                 continue # Ocultar entidades detrás del panel
            
            elif isinstance(entidad, Burbuja):
                entidad.dibujar(self.screen, shake_offset)
                
            else:
                rect_dibujo = entidad.rect.move(shake_offset)

                if isinstance(entidad, Planta):
                    if 'alga' in self.assets:
                        self.screen.blit(self.assets['alga'], rect_dibujo)
                    else:
                        pygame.draw.circle(self.screen, VERDE, rect_dibujo.center, 7)
                
                elif isinstance(entidad, Pez):
                    if 'pez' in self.assets:
                        sprite = self.assets['pez']
                        if entidad.direccion_h == -1:
                            sprite = pygame.transform.flip(sprite, True, False)
                        self.screen.blit(sprite, rect_dibujo)
                    else:
                        pygame.draw.circle(self.screen, AZUL, rect_dibujo.center, 10)
                
                elif isinstance(entidad, Trucha):
                    if 'trucha' in self.assets:
                        sprite = self.assets['trucha']
                        if entidad.direccion_h == -1:
                            sprite = pygame.transform.flip(sprite, True, False)
                        self.screen.blit(sprite, rect_dibujo)
                    else:
                        pygame.draw.circle(self.screen, MARRON, rect_dibujo.center, 17)
                
                elif isinstance(entidad, Tiburon):
                    if 'tiburon' in self.assets:
                        sprite = self.assets['tiburon']
                        if entidad.direccion_h == -1:
                            sprite = pygame.transform.flip(sprite, True, False)
                        self.screen.blit(sprite, rect_dibujo)
                    else:
                        pygame.draw.circle(self.screen, GRIS, rect_dibujo.center, 22)

        # 2. Dibujar el Panel Lateral (UI) encima de todo
        # El panel lateral NO vibra (no se le pasa shake_offset)
        self.dibujar_panel_lateral(ecosistema)
        
        # 3. Dibujar partículas (encima de la simulación, pero debajo del overlay)
        # Sí vibran, para que parezcan "del mundo"
        self.gestionar_eventos(ecosistema.eventos_visuales)
        self.actualizar_y_dibujar_particulas(shake_offset)
        
        # 4. Dibujar Overlay de Pausa (encima de todo, excepto el panel)
        if self.sim_running and self.sim_paused:
            self.dibujar_overlay_pausa(shake_offset)

        pygame.display.flip()

    # --- Métodos de Dibujo de la UI (Widgets) ---

    def dibujar_panel_lateral(self, ecosistema):
        """Dibuja el panel lateral completo y todos sus widgets."""
        if not self.font_normal:
            return
            
        # Dibujar el fondo del panel
        panel_surf = pygame.Surface((self.panel_ancho, self.height), pygame.SRCALPHA)
        panel_surf.fill(COLOR_PANEL_FONDO)
        self.screen.blit(panel_surf, (self.panel_rect.x, 0))
        
        # Obtener posición del mouse para Hovers
        mouse_pos = pygame.mouse.get_pos()
        
        # Título del Panel
        titulo_img = self.font_titulo.render("Panel de Control", True, COLOR_TEXTO_TITULO)
        self.screen.blit(titulo_img, (self.panel_rect.x + self.panel_padding, self.panel_padding))
        
        # Dibujar widgets
        self._dibujar_controles_principales(mouse_pos)
        
        # La UI cambia dependiendo de si la simulación está corriendo
        if self.sim_running:
            self._dibujar_stats_simulacion(ecosistema)
        else:
            self._dibujar_config_previa(mouse_pos)

    def _dibujar_controles_principales(self, mouse_pos):
        """Dibuja los botones Start, Pause, Stop."""
        
        # Botón Start/Comenzar (solo se muestra si NO está corriendo)
        if not self.sim_running:
            self._dibujar_boton(self.btn_start, COLOR_START, "Comenzar", 
                                hover_color=BLANCO)
        
        # Botones Pause y Stop (solo si la simulación está corriendo)
        if self.sim_running:
            if self.sim_paused:
                self._dibujar_boton(self.btn_pause, COLOR_RESUME, "Reanudar", 
                                    hover_color=BLANCO)
            else:
                self._dibujar_boton(self.btn_pause, COLOR_PAUSE, "Pausar", NEGRO_UI, 
                                    hover_color=BLANCO)
                
            self._dibujar_boton(self.btn_stop, COLOR_STOP, "Detener", 
                                hover_color=BLANCO)

    def _dibujar_config_previa(self, mouse_pos):
        """(Req 2) Dibuja el widget de configuración +/- con imágenes."""
        base_y = self.cfg_rows[0]['img_rect'].top - 30
        titulo_img = self.font_titulo.render("Configuración Inicial", True, COLOR_TEXTO_TITULO)
        self.screen.blit(titulo_img, (self.panel_rect.x + self.panel_padding, base_y))

        for row in self.cfg_rows:
            # --- (Req 2) Dibujar Imagen/Sprite ---
            asset = self.assets.get(row['asset_key'])
            if asset:
                # Centrar el asset en su rect
                asset_rect = asset.get_rect(center=row['img_rect'].center)
                self.screen.blit(asset, asset_rect)
            else:
                # Fallback: dibujar círculo de color
                pygame.draw.circle(self.screen, row['color'], row['img_rect'].center, 10)

            # Etiqueta (ej: "Algas")
            lbl_img = self.font_normal.render(row['label'], True, COLOR_TEXTO_NORMAL)
            lbl_pos = lbl_img.get_rect(centery=row['lbl_rect'].centery, left=row['lbl_rect'].left)
            self.screen.blit(lbl_img, lbl_pos)
            
            # --- Controles +/- con hover ---
            self._dibujar_boton(row['minus'], COLOR_SEPARADOR, "-", COLOR_TEXTO_TITULO, 
                                hover_color=BLANCO)
            self._dibujar_boton(row['plus'], COLOR_SEPARADOR, "+", COLOR_TEXTO_TITULO, 
                                hover_color=BLANCO)
            
            # Valor actual
            val = self.cfg[row['key']]
            val_img = self.font_normal.render(str(val), True, COLOR_TEXTO_TITULO)
            val_rect = val_img.get_rect(center=row['text_rect'].center)
            self.screen.blit(val_img, val_rect)

    def _dibujar_stats_simulacion(self, ecosistema):
        """(Req 1) Dibuja las estadísticas (SIN Tiempo y SIN Dominante)."""
        
        py = self.btn_stop.bottom + 30
        px = self.panel_rect.x + self.panel_padding
        ancho_total = self.panel_rect.width - (self.panel_padding * 2)

        # 1. Título
        titulo_img = self.font_titulo.render("Estadísticas", True, COLOR_TEXTO_TITULO)
        self.screen.blit(titulo_img, (px, py))
        py += 45 # Más espacio
        
        # 2. Progreso del Turno (Conservado)
        img_prog = self.font_pequeno.render("Siguiente Turno IA:", True, COLOR_TEXTO_NORMAL)
        self.screen.blit(img_prog, (px, py))
        py += 20
        rect_prog = pygame.Rect(px, py, ancho_total, 8)
        self._dibujar_barra_progreso(rect_prog, self.turn_progress, COLOR_RESUME, COLOR_BARRA_FONDO)
        py += 30
        
        # --- (Req 1) "Tiempo Transcurrido" y "Especie Dominante" ELIMINADOS ---
        
        # 3. Barras de Población (Conservado)
        self._dibujar_stats_poblacion(ecosistema, py)

    def _dibujar_stats_poblacion(self, ecosistema, start_y):
        """Dibuja las barras de población (Req 3: Barras de Progreso)."""
        px = self.panel_rect.x + self.panel_padding
        ancho_total = self.panel_rect.width - (self.panel_padding * 2)
        
        plantas, peces, truchas, tiburones = ecosistema.get_all_entities()
        counts = {
            'plantas': len(plantas),
            'peces': len(peces),
            'truchas': len(truchas),
            'tiburones': len(tiburones),
        }
        max_counts = {'plantas': 50, 'peces': 30, 'truchas': 15, 'tiburones': 10}
        labels = [('🌿 Algas','plantas'), ('🐟 Peces','peces'), ('🐠 Truchas','truchas'), ('🦈 Tiburones','tiburones')]
        colors = {'plantas': VERDE, 'peces': AZUL, 'truchas': MARRON, 'tiburones': GRIS}

        py = start_y
        for label, key in labels:
            count = counts[key]
            max_c = max_counts.get(key, count + 1)
            progress = min(1.0, count / float(max(1, max_c)))
            
            label_img = self.font_normal.render(f"{label} ({count})", True, COLOR_TEXTO_NORMAL)
            self.screen.blit(label_img, (px, py))
            py += 25
            
            rect_prog = pygame.Rect(px, py, ancho_total, 10)
            self._dibujar_barra_progreso(rect_prog, progress, colors[key], COLOR_BARRA_FONDO)
            py += 25 

    # --- Métodos de Gestión de Eventos y Estado ---

    def gestionar_eventos(self, eventos):
        """Lee la lista de eventos de la lógica y crea partículas."""
        if not self.font_particula:
            eventos.clear()
            return

        for evento in eventos:
            try:
                tipo = evento[0]
                pos = evento[1]
                
                # No crear partículas dentro del panel
                if pos[0] > self.panel_rect.left:
                    continue
                    
                pos_adj = (pos[0] + random.randint(-5, 5), pos[1] + random.randint(-5, 5))
                
                if tipo == 'comer_pez':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER))
                
                elif tipo == 'comer_depredador':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER, vida=60))
                    self.screen_shake = 10
                
                elif tipo == 'nacer':
                    self.particulas.append(Particula("❤️", pos_adj, COLOR_NACER, vida=60))
                
                elif tipo == 'morir':
                    self.particulas.append(Particula("💀", pos_adj, COLOR_MORIR, vida=60))
                    self.screen_shake = 8
            
            except Exception as e:
                print(f"Error procesando evento {evento}: {e}")
        
        eventos.clear()

    def actualizar_y_dibujar_particulas(self, offset=(0,0)):
        """Mueve, dibuja y elimina las partículas de efectos visuales."""
        if not self.font_particula:
            return
            
        for i in range(len(self.particulas) - 1, -1, -1):
            p = self.particulas[i]
            p.actualizar()
            
            if p.vida <= 0:
                self.particulas.pop(i)
            else:
                p.dibujar(self.screen, self.font_particula, offset)

    def set_estado_simulacion(self, sim_running, sim_paused):
        """Recibe el estado desde main.py y lo guarda."""
        self.sim_running = sim_running
        self.sim_paused = sim_paused

    def get_config_counts(self):
        """Devuelve los conteos elegidos en la configuración previa."""
        return {
            'plantas': int(self.cfg.get('plantas', 25)),
            'peces': int(self.cfg.get('peces', 15)),
            'truchas': int(self.cfg.get('truchas', 5)),
            'tiburones': int(self.cfg.get('tiburones', 2)),
        }

    # --- Manejadores de Clics (Actualizados para el Panel) ---

    def handle_click(self, pos):
        """Manejador principal de clics, delega al panel correcto."""
        
        # Si el clic no está en el panel lateral, ignorarlo
        if not self.panel_rect.collidepoint(pos):
            return None
            
        # 1. Clics de Configuración (solo si no está corriendo)
        if not self.sim_running:
            for row in self.cfg_rows:
                if row['minus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = max(0, self.cfg[k] - 1)
                    return 'cfg_changed'
                if row['plus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = min(200, self.cfg[k] + 1) # Límite de 200
                    return 'cfg_changed'
                    
        # 2. Clics de Control (Start/Pause/Stop)
        return self.hit_button(pos)

    def hit_button(self, pos):
        """Comprueba si un click (pos) ha golpeado un botón de control."""
        # Los botones ya están en coordenadas de pantalla, no necesitan offset
        if self.btn_start.collidepoint(pos) and not self.sim_running:
            return 'start'
        if self.btn_pause.collidepoint(pos) and self.sim_running:
            return 'pause'
        if self.btn_stop.collidepoint(pos) and self.sim_running:
            return 'stop'
        return None

    def cerrar(self):
        pygame.quit()

    # --- Setters para estadísticas (Implementado) ---
    def update_stats(self, turn_progress, sim_minutes, top_species, scores=None):
        """Recibe los datos de main.py y los guarda."""
        try:
            self.turn_progress = float(turn_progress)
        except Exception:
            self.turn_progress = 0.0
            
        try:
            self.sim_minutes = max(0, int(sim_minutes or 0))
        except Exception:
            self.sim_minutes = 0
            
        self.top_species = top_species or "N/A"
        self.scores = scores or {}