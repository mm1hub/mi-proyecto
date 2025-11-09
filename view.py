import os
import pygame
import random
from logic import (
    BLANCO, AZUL, VERDE, MARRON, GRIS,
    AGUA_CLARA, AGUA_OSCURA, NEGRO_UI,
    COLOR_TEXTO_BTN, COLOR_START, COLOR_STOP, COLOR_PAUSE, COLOR_RESUME,
    TEXTURAS, TEXTURAS_TAM,
    COLOR_COMER, COLOR_NACER, COLOR_MORIR,
    # --- (IDEA 10) Importar color de burbuja ---
    COLOR_BURBUJA,
    # Importar clases de entidades para isinstance
    Planta, Pez, Trucha, Tiburon,
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
        # --- (IDEA 1) Añadir un rect para Z-Sorting ---
        # El rect se actualiza en 'actualizar'
        self.rect = pygame.Rect(self.x, self.y, 20, 20) 

    def actualizar(self):
        """Mueve la partícula hacia arriba y reduce su vida."""
        self.y += self.velocidad_y
        self.vida -= 1
        if self.vida < self.vida_maxima / 2:
            self.alpha = int(255 * (self.vida / (self.vida_maxima / 2)))
        self.alpha = max(0, min(255, self.alpha))
        # Actualizar rect para Z-sorting
        self.rect.topleft = (int(self.x), int(self.y))

    def dibujar(self, screen, font, offset=(0,0)):
        """Dibuja el texto de la partícula."""
        try:
            img = font.render(self.texto, True, self.color)
            img.set_alpha(self.alpha)
            # --- (IDEA 9) Aplicar offset de screen shake ---
            screen.blit(img, (int(self.x + offset[0]), int(self.y + offset[1])))
        except Exception as e:
            print(f"Error al dibujar partícula: {e}")

# --- (IDEA 10) Clase para Burbujas ---
class Burbuja:
    """Una burbuja que sube y se desvanece."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vida_maxima = random.randint(60, 120) # Vida en frames
        self.vida = self.vida_maxima
        self.velocidad_y = random.uniform(-1.0, -0.5)
        self.radio_max = random.randint(2, 5)
        self.radio = 1
        # --- (IDEA 1) Rect para Z-Sorting ---
        self.rect = pygame.Rect(self.x - self.radio, self.y - self.radio, self.radio*2, self.radio*2)

    def actualizar(self):
        self.y += self.velocidad_y
        self.vida -= 1
        # Crece al inicio, se encoge al final
        if self.vida > self.vida_maxima - 10:
             self.radio = int(self.radio_max * ( (self.vida_maxima - self.vida) / 10.0) )
        elif self.vida < 20:
            self.radio = int(self.radio_max * (self.vida / 20.0))
        else:
            self.radio = self.radio_max
        self.radio = max(1, self.radio)
        # Actualizar rect para Z-sorting
        self.rect.center = (int(self.x), int(self.y))
    
    def dibujar(self, screen, offset=(0,0)):
        """Dibuja la burbuja como un círculo semi-transparente."""
        if self.radio < 1:
            return
            
        # Crear una superficie para la transparencia
        surf = pygame.Surface((self.radio*2, self.radio*2), pygame.SRCALPHA)
        # Dibujar el círculo en la superficie
        alpha = int(90 * (self.vida / self.vida_maxima)) # Desvanecer con la vida
        color_con_alpha = COLOR_BURBUJA + (alpha,)
        pygame.draw.circle(surf, color_con_alpha, (self.radio, self.radio), self.radio)
        
        # --- (IDEA 9) Aplicar offset de screen shake ---
        screen.blit(surf, (self.rect.x + offset[0], self.rect.y + offset[1]))


class Vista:
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema Acuático")
        self.assets = self.cargar_assets_flexible()
        
        self.fondo_superficie = self._crear_fondo_estatico(width, height)
        
        try:
            self.font = pygame.font.SysFont(None, 30)
            self.font_overlay = pygame.font.SysFont(None, 100)
            self.font_particula = pygame.font.SysFont('Arial', 18, bold=True)
        except:
            print("Warning: No se pudo cargar la fuente. La UI no se mostrará.")
            self.font = None
            self.font_overlay = None
            self.font_particula = None

        self.sim_running = False
        self.sim_paused = False
        
        self.btn_start = pygame.Rect(self.width - 450, 5, 120, 30)
        self.btn_pause = pygame.Rect(self.width - 320, 5, 120, 30)
        self.btn_stop = pygame.Rect(self.width - 190, 5, 120, 30)

        self.cfg = {
            'plantas': 25, 'peces': 15, 'truchas': 5, 'tiburones': 2,
        }
        self.cfg_rows = []
        base_y = 45
        row_h = 32
        labels = [('Algas','plantas'), ('Peces','peces'), ('Truchas','truchas'), ('Tiburones','tiburones')]
        for i, (label,key) in enumerate(labels):
            y = base_y + i * (row_h + 6)
            minus = pygame.Rect(150, y, 30, row_h)
            plus = pygame.Rect(150 + 120, y, 30, row_h)
            self.cfg_rows.append({'label': label, 'key': key, 'minus': minus, 'plus': plus, 'y': y, 'h': row_h})

        self.particulas = []
        # --- (IDEA 10) Lista para burbujas ---
        self.burbujas = []
        # --- (IDEA 9) Variable de Screen Shake ---
        self.screen_shake = 0

        # --- Estadisticas (UI) ---
        self.turn_progress = 0.0  # avance hacia el siguiente turno (0..1)
        self.sim_h = 0
        self.sim_m = 0
        self.top_species = None


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

    def _dibujar_boton(self, rect, color, texto, color_texto=COLOR_TEXTO_BTN, offset=(0,0)):
        # --- (IDEA 9) Aplicar offset ---
        rect_con_offset = rect.move(offset)
        pygame.draw.rect(self.screen, color, rect_con_offset, border_radius=5)
        if self.font:
            img_texto = self.font.render(texto, True, color_texto)
            pos_texto = img_texto.get_rect(center=rect_con_offset.center)
            self.screen.blit(img_texto, pos_texto)

    def dibujar_overlay_pausa(self, offset=(0,0)):
        if not self.font_overlay:
            return
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        # --- (IDEA 9) Aplicar offset ---
        self.screen.blit(overlay, offset)
        
        img_pausa = self.font_overlay.render("PAUSA", True, BLANCO)
        pos_pausa = img_pausa.get_rect(center=(self.width / 2 + offset[0], self.height / 2 + offset[1]))
        self.screen.blit(img_pausa, pos_pausa)


    def dibujar_ecosistema(self, ecosistema):
        
        # --- (IDEA 9) Calcular Screen Shake ---
        shake_offset = (0, 0)
        if self.screen_shake > 0:
            self.screen_shake -= 1
            shake_offset = (random.randint(-4, 4), random.randint(-4, 4))
            
        # Dibujar el fondo con el offset
        self.screen.blit(self.fondo_superficie, shake_offset)

        # --- (IDEA 10) Actualizar y crear burbujas ---
        # Actualizar burbujas existentes
        for i in range(len(self.burbujas) - 1, -1, -1):
            b = self.burbujas[i]
            b.actualizar()
            if b.vida <= 0:
                self.burbujas.pop(i)
        
        # Crear nuevas burbujas aleatoriamente (solo si no está pausado)
        if self.sim_running and not self.sim_paused:
            animales_que_respiran = ecosistema.peces + ecosistema.truchas
            if random.random() < 0.05: # Chance de 5% por frame
                if animales_que_respiran:
                    animal = random.choice(animales_que_respiran)
                    self.burbujas.append(Burbuja(animal.rect.centerx, animal.rect.top))

        # --- (IDEA 1) Z-Sorting (Falso 3D) ---
        # 1. Crear una lista única con todas las entidades
        todas_las_entidades = (
            ecosistema.plantas + 
            ecosistema.peces + 
            ecosistema.truchas + 
            ecosistema.tiburones +
            self.burbujas # Dibujar burbujas junto con todo lo demás
        )
        
        # 2. Ordenar la lista por la parte inferior (Y)
        todas_las_entidades.sort(key=lambda e: e.rect.bottom)
        
        # 3. Dibujar todo en orden
        for entidad in todas_las_entidades:
            
            # Calcular el rect de dibujo con el offset
            # (El rect de burbuja ya está en su centro, blit usará su topleft)
            if isinstance(entidad, Burbuja):
                entidad.dibujar(self.screen, shake_offset)
                continue # Saltar al siguiente
                
            rect_dibujo = entidad.rect.move(shake_offset)

            # --- DIBUJO POLIMÓRFICO ---
            
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


        # --- DIBUJO DE UI (Actualizado) ---
        self.dibujar_ui(ecosistema, shake_offset)
        
        # --- (IDEA 3) Procesar eventos y dibujar partículas ---
        self.gestionar_eventos(ecosistema.eventos_visuales)
        self.actualizar_y_dibujar_particulas(shake_offset)
        
        if self.sim_running and self.sim_paused:
            self.dibujar_overlay_pausa(shake_offset)

        pygame.display.flip()

    def dibujar_ui(self, ecosistema, offset=(0,0)):
        if not self.font:
            return
            
        # --- (IDEA 9) Aplicar offset al panel ---
        panel_rect = pygame.Rect(0, 0, self.width, 40).move(offset)
        panel_ui = pygame.Surface((self.width, 40), pygame.SRCALPHA)
        panel_ui.fill((240, 240, 240, 180))
        self.screen.blit(panel_ui, panel_rect.topleft)

        # Estadísticas (Lado izquierdo)
        textos = [
            (f"Algas: {len(ecosistema.plantas)}", VERDE, 10),
            (f"Peces: {len(ecosistema.peces)}", AZUL, 130),
            (f"Truchas: {len(ecosistema.truchas)}", MARRON, 260),
            (f"Tiburones: {len(ecosistema.tiburones)}", GRIS, 420),
        ]
        
        for (texto, color, x_pos) in textos:
            img = self.font.render(texto, True, NEGRO_UI) 
            # --- (IDEA 9) Aplicar offset al texto ---
            self.screen.blit(img, (x_pos + offset[0], 10 + offset[1]))
            
        # Panel de configuración previa
        if not self.sim_running:
            for row in self.cfg_rows:
                # --- (IDEA 9) Aplicar offset a todo ---
                lbl_img = self.font.render(row['label']+":", True, NEGRO_UI)
                self.screen.blit(lbl_img, (10 + offset[0], row['y'] + 5 + offset[1]))
                
                self._dibujar_boton(row['minus'], (200,200,200), "-", NEGRO_UI, offset)
                self._dibujar_boton(row['plus'], (200,200,200), "+", NEGRO_UI, offset)
                
                val = self.cfg[row['key']]
                val_img = self.font.render(str(val), True, NEGRO_UI)
                val_rect = val_img.get_rect(center=(row['minus'].right + 60 + offset[0], row['minus'].centery + offset[1]))
                self.screen.blit(val_img, val_rect)

        # Botones de control (Lado derecho)
        if not self.sim_running:
            self._dibujar_boton(self.btn_start, COLOR_START, "Comenzar", offset=offset)
        
        if self.sim_running:
            if self.sim_paused:
                self._dibujar_boton(self.btn_pause, COLOR_RESUME, "Reanudar", offset=offset)
            else:
                self._dibujar_boton(self.btn_pause, COLOR_PAUSE, "Pausar", NEGRO_UI, offset)
                
            self._dibujar_boton(self.btn_stop, COLOR_STOP, "Detener", offset=offset)

        # --- Estadisticas en tiempo real ---
        # Progreso del turno (barra a la derecha sin invadir botones)
        try:
            bar_w = 150
            bar_h = 8
            bar_x = self.width - 650 + offset[0]
            bar_y = 30 + offset[1]
            pygame.draw.rect(self.screen, (220,220,220), (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            p = max(0.0, min(1.0, float(self.turn_progress)))
            fill_w = int(bar_w * p)
            if fill_w > 0:
                pygame.draw.rect(self.screen, (80,180,80), (bar_x, bar_y, fill_w, bar_h), border_radius=4)
            lbl = self.font.render("Turno", True, NEGRO_UI)
            self.screen.blit(lbl, (bar_x - 55, bar_y - 6))
        except Exception:
            pass

        # Probabilidad de supervivencia (fila inferior izquierda del panel)
        try:
            top = self.top_species or "?"
            if top == 'peces': txt = 'Peces'
            elif top == 'truchas': txt = 'Truchas'
            elif top == 'tiburones': txt = 'Tiburones'
            else: txt = str(top)
            surv = self.font.render(f"Top: {txt}", True, NEGRO_UI)
            self.screen.blit(surv, (10 + offset[0], 24 + offset[1]))
        except Exception:
            pass

        # Tiempo de simulacion HH:MM (misma fila)
        try:
            hh = int(self.sim_h)
            mm = int(self.sim_m)
            timg = self.font.render(f"Tiempo: {hh:02d}:{mm:02d}", True, NEGRO_UI)
            self.screen.blit(timg, (200 + offset[0], 24 + offset[1]))
        except Exception:
            pass

    def gestionar_eventos(self, eventos):
        if not self.font_particula:
            eventos.clear()
            return

        for evento in eventos:
            try:
                tipo = evento[0]
                pos = evento[1]
                pos_adj = (pos[0] + random.randint(-5, 5), pos[1] + random.randint(-5, 5))
                
                if tipo == 'comer_pez':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER))
                
                # --- (IDEA 9) Activar Screen Shake para eventos grandes ---
                elif tipo == 'comer_depredador':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER, vida=60))
                    self.screen_shake = 10 # 10 frames de vibración
                
                elif tipo == 'nacer':
                    self.particulas.append(Particula("❤️", pos_adj, COLOR_NACER, vida=60))
                
                elif tipo == 'morir':
                    self.particulas.append(Particula("💀", pos_adj, COLOR_MORIR, vida=60))
                    self.screen_shake = 8 # Vibración más corta por muerte
            
            except Exception as e:
                print(f"Error procesando evento {evento}: {e}")
        
        eventos.clear()

    def actualizar_y_dibujar_particulas(self, offset=(0,0)):
        if not self.font_particula:
            return
            
        for i in range(len(self.particulas) - 1, -1, -1):
            p = self.particulas[i]
            p.actualizar()
            
            if p.vida <= 0:
                self.particulas.pop(i)
            else:
                # --- (IDEA 9) Pasar offset al dibujar ---
                p.dibujar(self.screen, self.font_particula, offset)

    def set_estado_simulacion(self, sim_running, sim_paused):
        self.sim_running = sim_running
        self.sim_paused = sim_paused

    def get_config_counts(self):
        return {
            'plantas': int(self.cfg.get('plantas', 25)),
            'peces': int(self.cfg.get('peces', 15)),
            'truchas': int(self.cfg.get('truchas', 5)),
            'tiburones': int(self.cfg.get('tiburones', 2)),
        }

    def handle_click(self, pos):
        # El click no necesita offset, porque 'pos' es la posición real del mouse
        if not self.sim_running:
            for row in self.cfg_rows:
                if row['minus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = max(0, self.cfg[k] - 1)
                    return 'cfg_changed'
                if row['plus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = min(200, self.cfg[k] + 1)
                    return 'cfg_changed'
        return self.hit_button(pos)

    def hit_button(self, pos):
        if self.btn_start.collidepoint(pos) and not self.sim_running:
            return 'start'
        if self.btn_pause.collidepoint(pos) and self.sim_running:
            return 'pause'
        if self.btn_stop.collidepoint(pos) and self.sim_running:
            return 'stop'
        return None

    def cerrar(self):
        pygame.quit()

    # --- Setters para estadisticas ---
    def update_stats(self, turn_progress, sim_minutes, top_species):
        try:
            self.turn_progress = float(turn_progress)
        except Exception:
            self.turn_progress = 0.0
        try:
            sim_minutes = max(0, int(sim_minutes or 0))
        except Exception:
            sim_minutes = 0
        self.sim_h = sim_minutes // 60
        self.sim_m = sim_minutes % 60
        self.top_species = top_species
