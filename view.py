import os
import pygame
import random # Necesario para el offset de partículas
from logic import (
    BLANCO, AZUL, VERDE, MARRON, GRIS, 
    AGUA_CLARA, AGUA_OSCURA, NEGRO_UI,
    COLOR_TEXTO_BTN, COLOR_START, COLOR_STOP, COLOR_PAUSE, COLOR_RESUME,
    TEXTURAS, TEXTURAS_TAM,
    # --- (IDEA 3) Importar colores de eventos ---
    COLOR_COMER, COLOR_NACER, COLOR_MORIR
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
        self.alpha = 255 # Para desvanecer

    def actualizar(self):
        """Mueve la partícula hacia arriba y reduce su vida."""
        self.y += self.velocidad_y
        self.vida -= 1
        # Calcular alpha para desvanecerse en la última mitad de vida
        if self.vida < self.vida_maxima / 2:
            self.alpha = int(255 * (self.vida / (self.vida_maxima / 2)))
        self.alpha = max(0, min(255, self.alpha)) # Asegurar que esté entre 0 y 255

    def dibujar(self, screen, font):
        """Dibuja el texto de la partícula."""
        try:
            # Crear superficie de texto y aplicar alpha
            img = font.render(self.texto, True, self.color)
            img.set_alpha(self.alpha)
            screen.blit(img, (int(self.x), int(self.y)))
        except Exception as e:
            # Evitar crash si la fuente falló o algo salió mal
            print(f"Error al dibujar partícula: {e}")


class Vista:
    def __init__(self, width, height):
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Simulador de Ecosistema Acuático")
        self.assets = self.cargar_assets_flexible()
        
        # --- MEJORA 1: Pre-renderizar el fondo de gradiente ---
        self.fondo_superficie = self._crear_fondo_estatico(width, height)
        
        try:
            self.font = pygame.font.SysFont(None, 30)
            self.font_overlay = pygame.font.SysFont(None, 100)
            # --- (IDEA 3) Fuente para partículas ---
            self.font_particula = pygame.font.SysFont('Arial', 18, bold=True)
        except:
            print("Warning: No se pudo cargar la fuente. La UI no se mostrará.")
            self.font = None
            self.font_overlay = None
            self.font_particula = None # Marcar como None si falla

        # --- NUEVO: Estado de la simulación ---
        self.sim_running = False
        self.sim_paused = False
        
        # --- NUEVO: Definición de botones ---
        # (x, y, ancho, alto)
        self.btn_start = pygame.Rect(self.width - 450, 5, 120, 30)
        self.btn_pause = pygame.Rect(self.width - 320, 5, 120, 30)
        self.btn_stop = pygame.Rect(self.width - 190, 5, 120, 30)

        # Configuración previa de cantidades por defecto
        self.cfg = {
            'plantas': 25,
            'peces': 15,
            'truchas': 5,
            'tiburones': 2,
        }
        # Rectángulos +/- para cada fila de configuración
        self.cfg_rows = []
        base_y = 45
        row_h = 32
        labels = [('Algas','plantas'), ('Peces','peces'), ('Truchas','truchas'), ('Tiburones','tiburones')]
        for i, (label,key) in enumerate(labels):
            y = base_y + i * (row_h + 6)
            minus = pygame.Rect(150, y, 30, row_h)
            plus = pygame.Rect(150 + 120, y, 30, row_h)
            self.cfg_rows.append({'label': label, 'key': key, 'minus': minus, 'plus': plus, 'y': y, 'h': row_h})

        # --- (IDEA 3) Lista para partículas activas ---
        self.particulas = []


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

    # Cargador flexible que resuelve rutas y nombres alternativos
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

        # Usar los diccionarios de configuración de logic.py
        for key, names in TEXTURAS.items():
            size = TEXTURAS_TAM.get(key, (20, 20)) # Usar tamaño por defecto si no se define
            img = try_load(names, size)
            if img:
                assets[key] = img
        
        if assets:
            print(f"Assets cargados: {list(assets.keys())} desde '{assets_dir}'.")
        else:
            print(f"Advertencia: no se cargó ninguna imagen desde '{assets_dir}'. Se usarán formas básicas.")
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

        # --- DIBUJO DE ENTIDADES (Con Idea 2) ---
        # Plantas
        for planta in ecosistema.plantas:
            if 'alga' in self.assets:
                self.screen.blit(self.assets['alga'], planta.rect)
            else:
                pygame.draw.circle(self.screen, VERDE, planta.rect.center, 7)

        # Peces
        for pez in ecosistema.peces:
            if 'pez' in self.assets:
                sprite = self.assets['pez']
                # --- (IDEA 2) Voltear sprite basado en la dirección ---
                if pez.direccion_h == -1:
                    sprite = pygame.transform.flip(sprite, True, False)
                self.screen.blit(sprite, pez.rect)
            else:
                pygame.draw.circle(self.screen, AZUL, pez.rect.center, 10)

        # Truchas
        for trucha in ecosistema.truchas:
            if 'trucha' in self.assets:
                sprite = self.assets['trucha']
                # --- (IDEA 2) Voltear sprite basado en la dirección ---
                if trucha.direccion_h == -1:
                    sprite = pygame.transform.flip(sprite, True, False)
                self.screen.blit(sprite, trucha.rect)
            else:
                pygame.draw.circle(self.screen, MARRON, trucha.rect.center, 17)

        # Tiburones
        for tiburon in ecosistema.tiburones:
            if 'tiburon' in self.assets:
                sprite = self.assets['tiburon']
                # --- (IDEA 2) Voltear sprite basado en la dirección ---
                if tiburon.direccion_h == -1:
                    sprite = pygame.transform.flip(sprite, True, False)
                self.screen.blit(sprite, tiburon.rect)
            else:
                pygame.draw.circle(self.screen, GRIS, tiburon.rect.center, 22)

        # --- DIBUJO DE UI (Actualizado) ---
        self.dibujar_ui(ecosistema)
        
        # --- (IDEA 3) Procesar eventos y dibujar partículas ---
        # (Se dibuja después de la UI para que las partículas estén sobre el panel)
        self.gestionar_eventos(ecosistema.eventos_visuales)
        self.actualizar_y_dibujar_particulas()
        
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
            
        # Panel de configuración previa (antes de iniciar)
        if not self.sim_running:
            for row in self.cfg_rows:
                # etiqueta
                lbl_img = self.font.render(row['label']+":", True, NEGRO_UI)
                self.screen.blit(lbl_img, (10, row['y'] + 5))
                # controles
                self._dibujar_boton(row['minus'], (200,200,200), "-", NEGRO_UI) # Texto negro
                self._dibujar_boton(row['plus'], (200,200,200), "+", NEGRO_UI) # Texto negro
                # valor actual
                val = self.cfg[row['key']]
                val_img = self.font.render(str(val), True, NEGRO_UI)
                val_rect = val_img.get_rect(center=(row['minus'].right + 60, row['minus'].centery)) # Más espacio
                self.screen.blit(val_img, val_rect)

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
                self._dibujar_boton(self.btn_pause, COLOR_PAUSE, "Pausar", NEGRO_UI) # Texto negro
                
            self._dibujar_boton(self.btn_stop, COLOR_STOP, "Detener")

    # --- (IDEA 3) Nuevo método para crear partículas desde eventos ---
    def gestionar_eventos(self, eventos):
        """Lee la lista de eventos de la lógica y crea partículas."""
        if not self.font_particula: # No crear partículas si la fuente falló
            eventos.clear()
            return

        for evento in eventos:
            try:
                tipo = evento[0]
                pos = evento[1]
                
                # Añadir un pequeño offset aleatorio para que no se apilen
                pos_adj = (pos[0] + random.randint(-5, 5), pos[1] + random.randint(-5, 5))
                
                if tipo == 'comer':
                    valor = evento[2]
                    self.particulas.append(Particula(f"+{valor}", pos_adj, COLOR_COMER))
                elif tipo == 'nacer':
                    self.particulas.append(Particula("❤️", pos_adj, COLOR_NACER, vida=60))
                elif tipo == 'morir':
                    # Añadir múltiples partículas para un efecto de "explosión"
                    for _ in range(5):
                        vel_x = random.uniform(-1, 1)
                        vel_y = random.uniform(-1, 1)
                        # Creamos una partícula simple sin texto, que podríamos dibujar como círculo
                        # Por ahora, usamos un emoji simple
                        self.particulas.append(Particula("💀", pos_adj, COLOR_MORIR, vida=30, velocidad_y=vel_y))
            except Exception as e:
                print(f"Error procesando evento {evento}: {e}")
        
        # Limpiar la lista de eventos de la lógica para no procesarlos de nuevo
        eventos.clear()

    # --- (IDEA 3) Nuevo método para actualizar y dibujar partículas ---
    def actualizar_y_dibujar_particulas(self):
        """Mueve, dibuja y elimina las partículas de efectos visuales."""
        if not self.font_particula:
            return
            
        # Iterar hacia atrás para poder eliminar elementos de forma segura
        for i in range(len(self.particulas) - 1, -1, -1):
            p = self.particulas[i]
            p.actualizar()
            
            if p.vida <= 0:
                self.particulas.pop(i)
            else:
                p.dibujar(self.screen, self.font_particula)

    # --- NUEVO: Método requerido por main.py ---
    def set_estado_simulacion(self, sim_running, sim_paused):
        """Recibe el estado desde main.py y lo guarda."""
        self.sim_running = sim_running
        self.sim_paused = sim_paused

    # Devuelve los conteos elegidos en la configuración previa
    def get_config_counts(self):
        return {
            'plantas': int(self.cfg.get('plantas', 25)),
            'peces': int(self.cfg.get('peces', 15)),
            'truchas': int(self.cfg.get('truchas', 5)),
            'tiburones': int(self.cfg.get('tiburones', 2)),
        }

    # Maneja clics de UI: primero configuración, luego botones estándar
    def handle_click(self, pos):
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