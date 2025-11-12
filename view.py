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
    # Importar clases de entidades para 'isinstance'.
    # La Vista necesita "leer" el tipo del Modelo para saber qué dibujar.
    Planta, Pez, Trucha, Tiburon,
    # Importar nuevos colores de UI
    Color, COLOR_PANEL_FONDO, COLOR_TEXTO_TITULO, COLOR_TEXTO_NORMAL,
    COLOR_BARRA_FONDO, COLOR_BARRA_PROGRESO, COLOR_SEPARADOR,
    WIDTH, HEIGHT # Importar dimensiones
)

"""Capa de presentación: dibuja el ecosistema y maneja la interfaz de usuario."""

# Relaciona eventos simbolicos con archivos ubicados en la carpeta de assets.
# Un 'map' nos da flexibilidad para cambiar los sonidos sin tocar la lógica.
SONIDOS_MAP = {
    'comer_pez': 'comer_planta.mp3',
    'comer_depredador': 'comer.mp3',
    'morir': 'morir.mp3',
    'start': 'comer.mp3',
    'pause': 'morir.mp3',
    'resume': 'comer_planta.mp3',
    'stop': 'morir.mp3',
}

# --- (IDEA 3) Clase para Efectos Visuales ---
# Encapsulamos los efectos visuales en sus propias clases.
# Esto limpia el bucle de dibujo principal.
class Particula:
    """Gestiona un texto flotante para eventos (comer, nacer, morir)."""
    def __init__(self, texto, pos, color, vida=45, velocidad_y=-0.5):
        # Se almacena la posición como floats para obtener desplazamientos suaves.
        self.x, self.y = pos
        self.texto = texto
        self.color = color
        self.vida_maxima = vida
        self.vida = vida  # Contador de vida (en frames)
        self.velocidad_y = velocidad_y
        self.alpha = 255
        self.rect = pygame.Rect(self.x, self.y, 20, 20) 

    def actualizar(self):
        """Mueve la partícula hacia arriba y reduce su vida."""
        self.y += self.velocidad_y
        self.vida -= 1
        # A mitad de vida comienza a desvanecerse para simular fading.
        if self.vida < self.vida_maxima / 2:
            self.alpha = int(255 * (self.vida / (self.vida_maxima / 2)))
        self.alpha = max(0, min(255, self.alpha))
        self.rect.topleft = (int(self.x), int(self.y))

    def dibujar(self, screen, font, offset=(0,0)):
        """Dibuja el texto de la partícula."""
        try:
            # El 'render' de texto es costoso, pero para partículas efímeras es aceptable.
            img = font.render(self.texto, True, self.color)
            img.set_alpha(self.alpha) # Aplicamos el 'fading'
            screen.blit(img, (int(self.x + offset[0]), int(self.y + offset[1])))
        except Exception as e:
            pass # Evitar crash si la fuente falla

# --- (IDEA 10) Clase para Burbujas ---
class Burbuja:
    """Una burbuja que sube y se desvanece."""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vida_maxima = random.randint(60, 120) # Vidas aleatorias para variedad
        self.vida = self.vida_maxima
        self.velocidad_y = random.uniform(-1.0, -0.5)
        self.radio_max = random.randint(2, 5)
        self.radio = 1
        self.rect = pygame.Rect(self.x - self.radio, self.y - self.radio, self.radio*2, self.radio*2)

    def actualizar(self):
        """Mueve la burbuja hacia arriba y ajusta su radio."""
        self.y += self.velocidad_y
        self.vida -= 1
        # Simulamos el "crecimiento" y "explosión" de la burbuja.
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
            # Dibujar con transparencia requiere una 'Surface' temporal.
            surf = pygame.Surface((self.radio*2, self.radio*2), pygame.SRCALPHA)
            alpha = int(90 * (self.vida / self.vida_maxima)) # Fading
            alpha = max(0, min(255, alpha))
            color_con_alpha = (
                COLOR_BURBUJA.r,
                COLOR_BURBUJA.g,
                COLOR_BURBUJA.b,
                alpha,
            )
            pygame.draw.circle(surf, color_con_alpha, (self.radio, self.radio), self.radio)
            
            # Aplicar offset y dibujar
            screen.blit(surf, (self.rect.x + offset[0], self.rect.y + offset[1]))
        except Exception:
            pass # Evitar crash si el radio es inválido

# --- Clase Vista Principal (Rediseñada) ---
# Esta es la clase principal de la capa de presentación.
class Vista:
    """Gestiona la ventana principal, panel lateral y todos los efectos visuales."""

    def __init__(self, width, height):
        """El "constructor" de la UI: prepara la ventana, carga fuentes y define la UI."""
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema Acuático")
        
        # Delegamos la carga de recursos a métodos especializados.
        self.assets = self.cargar_assets_flexible()  # Texturas precargadas por tipo de entidad.
        self.sonidos = self._cargar_sonidos()        # Clips cortos asociados a eventos.
        self.musica_activa = False
        
        # Optimizacion: El fondo degradado se pre-renderiza una sola vez.
        self.fondo_superficie = self._crear_fondo_estatico(width, height)
        
        # --- Carga de Fuentes ---
        # La carga de fuentes es "costosa", se hace una sola vez en el init.
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
        # La Vista necesita conocer el estado para decidir QUÉ dibujar (menú vs. stats)
        self.sim_running = False
        self.sim_paused = False

        # --- Definición del Panel Lateral (UI) ---
        # Definimos el 'layout' de la UI aquí. Usamos 'Rects' para clics y dibujo.
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
        # Este es el "modelo" de datos interno de la Vista para la configuración.
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
        
        # Generamos los 'Rects' para los controles +/-
        for i, (label, key, asset_key, color) in enumerate(cfg_data):
            y = base_y + i * 40
            # Layout: [IMG] [Label]... [ - ] [ 5 ] [ + ]
            img_rect = pygame.Rect(px, y, 30, 30)
            lbl_rect = pygame.Rect(img_rect.right + 5, y, 90, 30)
            minus_rect = pygame.Rect(lbl_rect.right + 5, y, 30, 30)
            text_rect = pygame.Rect(minus_rect.right, y, 40, 30) # Más espacio para números
            plus_rect = pygame.Rect(text_rect.right, y, 30, 30)
            
            # Guardamos todos los rects involucrados para reutilizarlos en el render y hit-test.
            self.cfg_rows.append({
                'label': label, 'key': key, 'asset_key': asset_key, 'color': color,
                'img_rect': img_rect, 'lbl_rect': lbl_rect,
                'minus': minus_rect, 'plus': plus_rect, 'text_rect': text_rect
            })

        # --- Partículas y Efectos ---
        self.particulas = []
        self.burbujas = []
        self.screen_shake = 0 # Un simple contador para el efecto "vibración"
        
        # --- Almacén de Estadísticas (de main.py) ---
        self.turn_progress = 0.0

    def _crear_fondo_estatico(self, width, height):
        """Genera un degradado simple que simula profundidad bajo el agua."""
        # Esto es una optimización: es más rápido 'blitear' una imagen
        # que dibujar 720 líneas en cada frame.
        fondo = pygame.Surface((width, height))
        for y in range(height):
            ratio = y / height  # Ratio 0..1 para interpolar entre azul claro y oscuro.
            r = int(AGUA_CLARA[0] * (1 - ratio) + AGUA_OSCURA[0] * ratio)
            g = int(AGUA_CLARA[1] * (1 - ratio) + AGUA_OSCURA[1] * ratio)
            b = int(AGUA_CLARA[2] * (1 - ratio) + AGUA_OSCURA[2] * ratio)
            color_interpolado = (r, g, b)
            pygame.draw.line(fondo, color_interpolado, (0, y), (width, y))
        return fondo

    def cargar_assets_flexible(self):
        """Un cargador robusto: busca assets y provee un 'fallback' a formas básicas."""
        assets = {}
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, 'assets')  # Carpeta compartida

        def try_load(names, size):
            """Busca la primera textura disponible y la escala al tamaño deseado."""
            for name in names:
                path = os.path.join(assets_dir, name)
                if os.path.isfile(path):
                    try:
                        img = pygame.image.load(path).convert_alpha()
                        return pygame.transform.scale(img, size)
                    except Exception as e:
                        print(f"Error cargando {path}: {e}")
            return None  # Si ninguna textura existe, se devolverá None.
        
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

    def _cargar_sonidos(self):
        """Carga los sonidos disponibles y prepara el mixer si es necesario."""
        sonidos = {}
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(base_dir, 'assets')

        if not os.path.isdir(assets_dir):
            return sonidos

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init() # Inicializa el subsistema de audio
            except Exception as exc:
                print(f"Audio deshabilitado (no se pudo inicializar mixer): {exc}")
                return sonidos

        cache = {} # Caché para evitar cargar el mismo archivo (ej. 'morir.mp3') varias veces
        for key, nombre in SONIDOS_MAP.items():
            ruta = os.path.join(assets_dir, nombre)
            if not os.path.isfile(ruta):
                continue
            if nombre in cache:
                sonidos[key] = cache[nombre]
                continue
            try:
                sonido = pygame.mixer.Sound(ruta)
                cache[nombre] = sonido
                sonidos[key] = sonido
            except Exception as exc:
                print(f"Error cargando sonido {ruta}: {exc}")

        if sonidos:
            print(f"Sonidos cargados: {sorted(sonidos.keys())}")
        else:
            print("Advertencia: no se pudo cargar ningún sonido; audio deshabilitado.")
        return sonidos

    def iniciar_musica_fondo(self, volumen=5.0):
        """Carga y reproduce la pista base en loop suave."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ruta_musica = os.path.join(base_dir, 'assets', 'musica_fondo_mar.mp3')
        if not os.path.isfile(ruta_musica):
            return # La música es opcional

        if self.musica_activa and pygame.mixer.get_init() and pygame.mixer.music.get_busy():
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volumen)))
            return

        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except Exception as exc:
                print(f"No se pudo inicializar mixer para la música de fondo: {exc}")
                return

        try:
            pygame.mixer.music.load(ruta_musica)
            pygame.mixer.music.set_volume(max(0.0, min(1.0, volumen)))
            pygame.mixer.music.play(loops=-1) # -1 significa loop infinito
            self.musica_activa = True
        except Exception as exc:
            print(f"Error reproduciendo música de fondo: {exc}")

    def reproducir_sonido(self, clave, volumen=0.65):
        """Reproduce el sonido asociado a la clave si fue cargado."""
        if not self.sonidos:
            return
        sonido = self.sonidos.get(clave)
        if not sonido:
            return
        try:
            sonido.set_volume(max(0.0, min(1.0, volumen)))
            sonido.play()
        except Exception:
            pass # Cualquier fallo del mixer se ignora

    def _dibujar_boton(self, rect, color_base, texto, color_texto=COLOR_TEXTO_BTN, offset=(0,0), hover_color=None):
        """Un 'widget' privado para dibujar botones. Encapsula la lógica de renderizado."""
        rect_con_offset = rect.move(offset)  
        color = color_base
        
        # --- Efecto Hover (Idea 5) ---
        if hover_color and rect_con_offset.collidepoint(pygame.mouse.get_pos()):
            # Interpola el color (lerp) para un efecto suave
            color = color_base.lerp(hover_color, 0.3)
            
        pygame.draw.rect(self.screen, color, rect_con_offset, border_radius=5)
        # Renderizamos y centramos el texto dentro del botón.
        img_texto = self.font_normal.render(texto, True, color_texto)
        pos_texto = img_texto.get_rect(center=rect_con_offset.center)
        self.screen.blit(img_texto, pos_texto)

    def _dibujar_barra_progreso(self, rect, progress, color_fg, color_bg, offset=(0,0)):
        """Widget' privado para barras de progreso."""
        rect_con_offset = rect.move(offset)
        pygame.draw.rect(self.screen, color_bg, rect_con_offset, border_radius=4)
        progress = max(0, min(1, progress)) # Asegurar 0.0 a 1.0 (clamping)
        fg_rect = pygame.Rect(rect_con_offset.x, rect_con_offset.y, 
                              int(rect_con_offset.width * progress), rect_con_offset.height)
        pygame.draw.rect(self.screen, color_fg, fg_rect, border_radius=4)

    def dibujar_overlay_pausa(self, offset=(0,0)):
        """Dibuja el overlay de Pausa con offset."""
        if not self.font_overlay:
            return
        # El overlay cubre solo el área de simulación (no el panel)
        overlay_rect = pygame.Rect(0, 0, self.panel_rect.left, self.height)
        # Usamos una superficie con Alpha para el efecto "oscurecido"
        overlay = pygame.Surface(overlay_rect.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128)) # Negro semi-transparente
        self.screen.blit(overlay, (0,0)) 
        
        # El texto sí vibra con el 'shake_offset'
        img_pausa = self.font_overlay.render("PAUSA", True, BLANCO)
        pos_pausa = img_pausa.get_rect(center=(overlay_rect.centerx + offset[0], overlay_rect.centery + offset[1]))
        self.screen.blit(img_pausa, pos_pausa)

    # --- Bucle de Dibujo Principal ---

    def dibujar_ecosistema(self, ecosistema):
        """Este es el "corazón" del renderizado, llamado 60 veces por segundo desde main."""
        
        # Calculamos el 'offset' del screen shake.
        shake_offset = (0, 0)
        if self.screen_shake > 0:
            self.screen_shake -= 1 # El 'shake' se consume
            shake_offset = (random.randint(-4, 4), random.randint(-4, 4))
            
        # 1. Dibujar la simulación (fondo y entidades)
        # Aplicamos el 'shake_offset' al fondo.
        self.screen.blit(self.fondo_superficie, shake_offset)
        
        # Actualizar y crear burbujas (lógica puramente visual)
        for i in range(len(self.burbujas) - 1, -1, -1):
            b = self.burbujas[i]
            b.actualizar()
            if b.vida <= 0:
                self.burbujas.pop(i)
        
        # Creamos burbujas esporádicamente si la simulación corre
        if self.sim_running and not self.sim_paused:
            plantas, peces, truchas, tiburones = ecosistema.get_all_entities()
            animales_que_respiran = peces + truchas
            if random.random() < 0.05: # 5% de chance por frame
                if animales_que_respiran:
                    animal = random.choice(animales_que_respiran)
                    if animal.rect.centerx < self.panel_rect.left:
                        self.burbujas.append(Burbuja(animal.rect.centerx, animal.rect.top))
        else:
            plantas, peces, truchas, tiburones = [],[],[],[] # Vacío si no corre

        # Punto clave: Z-Sorting. Dibujamos las entidades de 'atrás' (Y más baja) primero.
        # Esto da una ilusión de profundidad.
        todas_las_entidades = (
            plantas + peces + truchas + tiburones + self.burbujas
        )
        todas_las_entidades.sort(key=lambda e: e.rect.bottom)
        
        # Bucle de renderizado de entidades
        for entidad in todas_las_entidades:
            # Ocultar entidades detrás del panel
            if entidad.rect.right > self.panel_rect.left:
                 continue 
            
            elif isinstance(entidad, Burbuja):
                entidad.dibujar(self.screen, shake_offset)
                
            else:
                # El 'rect' de la entidad se ajusta con el 'shake'
                rect_dibujo = entidad.rect.move(shake_offset)

                # Aquí es donde la Vista "lee" el Modelo usando 'isinstance'
                # y decide qué asset o forma dibujar.
                if isinstance(entidad, Planta):
                    if 'alga' in self.assets:
                        self.screen.blit(self.assets['alga'], rect_dibujo)
                    else:
                        # Fallback si no hay imagen
                        pygame.draw.circle(self.screen, VERDE, rect_dibujo.center, 7)
                
                elif isinstance(entidad, Pez):
                    if 'pez' in self.assets:
                        sprite = self.assets['pez']
                        # Giramos el sprite basado en la dirección (leída del modelo)
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

        # Finalmente, actualizamos la pantalla.
        pygame.display.flip()  # Intercambia buffers para mostrar el frame recién pintado.

    # --- Métodos de Dibujo de la UI (Widgets) ---

    def dibujar_panel_lateral(self, ecosistema):
        """Dibuja el panel lateral completo y todos sus widgets."""
        if not self.font_normal:
            return
            
        # Dibujar el fondo del panel (con transparencia)
        panel_surf = pygame.Surface((self.panel_ancho, self.height), pygame.SRCALPHA)
        panel_surf.fill(COLOR_PANEL_FONDO)
        self.screen.blit(panel_surf, (self.panel_rect.x, 0))
        
        mouse_pos = pygame.mouse.get_pos()
        
        # Título del Panel
        titulo_img = self.font_titulo.render("Panel de Control", True, COLOR_TEXTO_TITULO)
        self.screen.blit(titulo_img, (self.panel_rect.x + self.panel_padding, self.panel_padding))
        
        # Dibujar widgets
        self._dibujar_controles_principales(mouse_pos)
        
        # La UI es sensible al estado: muestra Config o Stats.
        if self.sim_running:
            self._dibujar_stats_simulacion(ecosistema)
        else:
            self._dibujar_config_previa(mouse_pos)

    def _dibujar_controles_principales(self, mouse_pos):
        """Dibuja los botones Start, Pause, Stop, usando el widget _dibujar_boton."""
        
        # Botón Start/Comenzar (solo se muestra si NO está corriendo)
        if not self.sim_running:
            self._dibujar_boton(self.btn_start, COLOR_START, "Comenzar", 
                                hover_color=BLANCO)
        
        # Botones Pause y Stop (solo si la simulación está corriendo)
        if self.sim_running:
            if self.sim_paused:
                # El botón de pausa cambia de texto y color.
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
                asset_rect = asset.get_rect(center=row['img_rect'].center)
                self.screen.blit(asset, asset_rect)
            else:
                # Fallback: dibujar círculo de color
                pygame.draw.circle(self.screen, row['color'], row['img_rect'].center, 10)

            # Etiqueta (ej: "Algas")
            lbl_img = self.font_normal.render(row['label'], True, COLOR_TEXTO_NORMAL)
            lbl_pos = lbl_img.get_rect(centery=row['lbl_rect'].centery, left=row['lbl_rect'].left)
            self.screen.blit(lbl_img, lbl_pos)
            
            # --- Controles +/- con hover (reutilizando el widget de botón) ---
            self._dibujar_boton(row['minus'], COLOR_SEPARADOR, "-", COLOR_TEXTO_TITULO, 
                                hover_color=BLANCO)
            self._dibujar_boton(row['plus'], COLOR_SEPARADOR, "+", COLOR_TEXTO_TITULO, 
                                hover_color=BLANCO)
            
            # Valor actual (leído del 'self.cfg' interno de la Vista)
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
        
        # 2. Progreso del Turno (Alimentado por 'update_stats' desde main)
        img_prog = self.font_pequeno.render("Siguiente Turno IA:", True, COLOR_TEXTO_NORMAL)
        self.screen.blit(img_prog, (px, py))
        py += 20
        rect_prog = pygame.Rect(px, py, ancho_total, 8)
        self._dibujar_barra_progreso(rect_prog, self.turn_progress, COLOR_RESUME, COLOR_BARRA_FONDO)
        py += 30
        
        # --- (Req 1) "Tiempo Transcurrido" y "Especie Dominante" ELIMINADOS ---
        
        # 3. Barras de Población (Leídas en vivo del modelo 'ecosistema')
        self._dibujar_stats_poblacion(ecosistema, py)

    def _dibujar_stats_poblacion(self, ecosistema, start_y):
        """Dibuja las barras de población (Req 3: Barras de Progreso)."""
        px = self.panel_rect.x + self.panel_padding
        ancho_total = self.panel_rect.width - (self.panel_padding * 2)
        
        # Leemos los datos del modelo 'ecosistema'
        plantas, peces, truchas, tiburones = ecosistema.get_all_entities()
        counts = {
            'plantas': len(plantas),
            'peces': len(peces),
            'truchas': len(truchas),
            'tiburones': len(tiburones),
        }
        # Usamos un 'max' fijo para que las barras sean comparables
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
        """Lee la lista de eventos de la lógica y crea partículas visuales."""
        if not self.font_particula:
            eventos.clear()
            return

        # 'eventos_visuales' es la cola que la Lógica llena y la Vista consume.
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
                    self.reproducir_sonido('comer_pez')
                
                elif tipo == 'comer_depredador':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER, vida=60))
                    self.screen_shake = 10 # Activamos el 'shake'
                    self.reproducir_sonido('comer_depredador')
                
                elif tipo == 'nacer':
                    self.particulas.append(Particula("❤️", pos_adj, COLOR_NACER, vida=60))
                
                elif tipo == 'morir':
                    self.particulas.append(Particula("💀", pos_adj, COLOR_MORIR, vida=60))
                    self.screen_shake = 8
                    self.reproducir_sonido('morir')
            
            except Exception as e:
                print(f"Error procesando evento {evento}: {e}")
        
        eventos.clear()  # La vista consume los eventos.

    def actualizar_y_dibujar_particulas(self, offset=(0,0)):
        """Mueve, dibuja y elimina las partículas de efectos visuales."""
        if not self.font_particula:
            return
            
        # Se recorre en reversa para eliminar partículas 'muertas' de forma segura.
        for i in range(len(self.particulas) - 1, -1, -1):
            p = self.particulas[i]
            p.actualizar()
            
            if p.vida <= 0:
                self.particulas.pop(i)
            else:
                p.dibujar(self.screen, self.font_particula, offset)

    # --- API de la Vista (Métodos llamados por Main.py) ---

    def set_estado_simulacion(self, sim_running, sim_paused):
        """Esta es la "entrada" de estado desde main.py."""
        self.sim_running = sim_running
        self.sim_paused = sim_paused

    def get_config_counts(self):
        """Esta es la "salida" de datos hacia main.py."""
        # Devuelve los valores de la UI de configuración.
        return {
            'plantas': int(self.cfg.get('plantas', 25)),
            'peces': int(self.cfg.get('peces', 15)),
            'truchas': int(self.cfg.get('truchas', 5)),
            'tiburones': int(self.cfg.get('tiburones', 2)),
        }

    # --- Manejadores de Clics (Actualizados para el Panel) ---

    def handle_click(self, pos):
        """Esta es la "salida" de la Vista. Traduce un clic (píxeles) a una acción (string)."""
        
        # Si el clic no está en el panel lateral, la Vista lo ignora.
        if not self.panel_rect.collidepoint(pos):
            return None
            
        # 1. Clics de Configuración (solo si no está corriendo)
        # La Vista maneja los clics de +/- internamente, actualizando 'self.cfg'.
        if not self.sim_running:
            for row in self.cfg_rows:
                if row['minus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = max(0, self.cfg[k] - 1)
                    return 'cfg_changed' # Notifica, aunque main no usa esto
                if row['plus'].collidepoint(pos):
                    k = row['key']
                    self.cfg[k] = min(200, self.cfg[k] + 1)
                    return 'cfg_changed'
                    
        # 2. Clics de Control (Start/Pause/Stop)
        # Delega a 'hit_button' para ver si se pulsó un botón de acción.
        return self.hit_button(pos)

    def hit_button(self, pos):
        """Comprueba si un click (pos) ha golpeado un botón de control."""
        # Comprobación simple de colisión de 'Rects'
        if self.btn_start.collidepoint(pos) and not self.sim_running:
            return 'start'
        if self.btn_pause.collidepoint(pos) and self.sim_running:
            return 'pause'
        if self.btn_stop.collidepoint(pos) and self.sim_running:
            return 'stop'
        return None # Si el clic fue en el panel pero no en un botón

    def cerrar(self):
        """Limpia los recursos de Pygame."""
        if pygame.mixer.get_init():
            try:
                pygame.mixer.music.stop()
                self.musica_activa = False
            except Exception:
                pass
        pygame.quit()  # Libera todos los subsistemas de Pygame.

    # --- Setters para estadísticas (Implementado) ---
    def update_stats(self, turn_progress):
        """Esta es la "entrada" de datos desde main.py. La Vista es 'alimentada' con estado."""
        try:
            self.turn_progress = float(turn_progress)
        except Exception:
            self.turn_progress = 0.0