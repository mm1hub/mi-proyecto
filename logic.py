import pygame
import random
from abc import ABC, abstractmethod
from pygame import Color # <-- Para efecto hover y 'lerp'

"""Define la logica central y describe las reglas de comportamiento del ecosistema."""

# El módulo expone tanto el modelo como los valores compartidos con la vista,
# de modo que se mantiene una única fuente de verdad para tamaños y colores.

# ---------------------------------
# CONFIGURACIÓN GLOBAL (compartida)
# ---------------------------------
WIDTH, HEIGHT = 1024, 768      # Resolucion base de la ventana (vista reutiliza).
FPS = 60                       # Se subio a 60 para dar mas suavidad visual.
TURNO_DURACION_MS = 1000       # Cada segundo se ejecuta un turno discreto de IA.
GRID_CELDA = 64                # Usado para experimentos de cuadricula (mantener coherencia).

# Colores (usados por la Vista, pero importados desde aquí)
# Se definen aquí para que la vista sólo sea responsable de dibujar.
BLANCO = Color(255, 255, 255)
AZUL = Color(0, 0, 255)
VERDE = Color(0, 255, 0)
MARRON = Color(139, 69, 19)
GRIS = Color(169, 169, 169)

# Configuración de texturas
# Cada clave representa un tipo de entidad y lista posibles nombres de archivo.
TEXTURAS = {
    'pez': ['pez.png', 'pez.gif', 'fish.png'],
    'trucha': ['trucha.png', 'trucha.gif'],
    'tiburon': ['tiburon.png', 'tiburon.gif', 'shark.png'],
    'alga': ['algagif.gif', 'alga.png', 'alga.gif'],
}

# Tamaños visuales de cada entidad
# La vista recurre a estos valores cuando carga texturas o dibuja formas fallback.
TEXTURAS_TAM = {
    'pez': (20, 20),
    'trucha': (35, 35),
    'tiburon': (45, 45),
    'alga': (14, 14),
}

# --- Colores para la VISTA (UI y Fondo) ---
# Se centralizan para poder cambiar el tema cromático desde la lógica.
AGUA_CLARA = Color(173, 216, 230)
AGUA_OSCURA = Color(0, 105, 148)
NEGRO_UI = Color(20, 20, 20) 

# --- Colores para BOTONES ---
# Inspirados en Bootstrap para mantener contraste suficiente en el panel.
COLOR_TEXTO_BTN = Color(255, 255, 255)
COLOR_START = Color(40, 167, 69)
COLOR_STOP = Color(220, 53, 69)
COLOR_PAUSE = Color(255, 193, 7)
COLOR_RESUME = Color(23, 162, 184)

# --- Colores para Partículas de Eventos ---
# Los efectos visuales usan estos valores para transmitir el tipo de evento.
COLOR_COMER = Color(144, 238, 144) 
COLOR_NACER = Color(255, 182, 193) 
COLOR_MORIR = Color(160, 160, 160) 
COLOR_BURBUJA = Color(200, 225, 255)

# --- NUEVOS COLORES PARA EL PANEL LATERAL ---
# Todos tienen inspiración Bootstrap para un look moderno.
COLOR_PANEL_FONDO = Color(33, 37, 41, 230) # Bootstrap Dark (con alpha)
COLOR_TEXTO_TITULO = Color(248, 249, 250) # Bootstrap Light
COLOR_TEXTO_NORMAL = Color(206, 212, 218) # Bootstrap Gray-400
COLOR_BARRA_FONDO = Color(73, 80, 87)
COLOR_BARRA_PROGRESO = Color(0, 123, 255) # Bootstrap Primary
COLOR_SEPARADOR = Color(108, 117, 125) # Bootstrap Gray-600


# ---------------------------------
# CAPA DE LÓGICA (MODELO)
# ---------------------------------

class Animal(ABC):
    """Modelo base para cualquier criatura con energia, edad y posicion."""

    def __init__(self, nombre, energia, tiempo_vida, ancho=10, alto=10):
        """Genera una entidad con posicion aleatoria y estados iniciales."""
        self.nombre = nombre
        self.energia = energia
        self.tiempo_vida = tiempo_vida
        self.edad = 0
        # El rect define la posición dibujable; inicia aleatoriamente en pantalla.
        self.rect = pygame.Rect(
            random.randint(0, max(0, WIDTH - ancho)),
            random.randint(0, max(0, HEIGHT - alto)),
            ancho,
            alto,
        )
        self.target_x = float(self.rect.x)
        self.target_y = float(self.rect.y)
        
        # --- CAMBIO: Velocidad reducida para 60 FPS ---
        self.velocidad_frame = random.uniform(0.5, 1.5) # Era 1.0 a 3.0

        self.pos_x = float(self.rect.x)  # Posición en float para interpolar suavemente.
        self.pos_y = float(self.rect.y)
        
        self.direccion_h = 1 # 1 = derecha, -1 = izquierda
        
        if self.rect.right > WIDTH: self.rect.right = WIDTH  # Se recorta por si spawn excede límites.
        if self.rect.bottom > HEIGHT: self.rect.bottom = HEIGHT
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.target_x, self.target_y = self.pos_x, self.pos_y

    @abstractmethod
    def decidir_objetivo(self, listas_de_seres):
        """Define la IA concreta de cada especie al elegir su destino."""

    @abstractmethod
    def comer(self, objetivo):
        """Resuelve como aumenta energia cuando la especie come algo."""

    @abstractmethod
    def reproducir(self):
        """Devuelve una nueva cria cuando la especie se reproduce."""

    def update_decision_turno(self, listas_de_seres):
        """Actualiza energia/edad y delega la seleccion de objetivos."""
        self.energia -= 2  # Cada turno consume energía base.
        self.edad += 1     # La edad avanza de forma discreta por turno.
        self.decidir_objetivo(listas_de_seres)

    def update_movimiento_frame(self):
        """Interpolacion suave hacia el objetivo elegido en el turno de IA."""
        # --- SOLUCIÓN TIRONES (IDEA 1) ---
        # Si el animal llega a su destino, ¡que vague!
        # No espera al próximo "turno de IA" para moverse.
        self._limitar_objetivo_a_pantalla()
        dist_x = abs(self.target_x - self.pos_x)
        dist_y = abs(self.target_y - self.pos_y)
        
        # Un umbral de 5px para considerar que "llegó"
        if dist_x < 5 and dist_y < 5:
            # Llegó, asignar un nuevo objetivo de "vagar" cercano
            self.target_x = self.pos_x + random.randint(-50, 50)
            self.target_y = self.pos_y + random.randint(-50, 50)
            
            # Limitar a la pantalla
            self._limitar_objetivo_a_pantalla()

        # --- Lógica de movimiento (como estaba antes) ---
        dx = self.target_x - self.pos_x  # Distancia restante en eje X.
        dy = self.target_y - self.pos_y  # Distancia restante en eje Y.
        
        if abs(dx) > 0.1: 
            step_x = max(-self.velocidad_frame, min(self.velocidad_frame, dx))
            self.pos_x += step_x
            self.direccion_h = 1 if step_x > 0 else -1 
        
        if abs(dy) > 0:
            # Limitamos el paso vertical a la velocidad del frame para evitar saltos.
            step_y = max(-self.velocidad_frame, min(self.velocidad_frame, dy))
            self.pos_y += step_y
            
        self._limitar_posicion_a_pantalla()

    def ha_muerto(self):
        """Evalua si el animal llego a su limite de vida o energia."""
        return self.edad >= self.tiempo_vida or self.energia <= 0

    def _limites_pantalla(self):
        """Retorna los valores maximos permitidos para topleft."""
        return max(0, WIDTH - self.rect.width), max(0, HEIGHT - self.rect.height)

    def _limitar_objetivo_a_pantalla(self):
        """Evita que el objetivo caiga fuera del rango visible."""
        max_x, max_y = self._limites_pantalla()
        self.target_x = max(0.0, min(self.target_x, float(max_x)))
        self.target_y = max(0.0, min(self.target_y, float(max_y)))

    def _limitar_posicion_a_pantalla(self):
        """Sincroniza la posicion flotante con el rect recortado a pantalla."""
        max_x, max_y = self._limites_pantalla()
        self.pos_x = max(0.0, min(self.pos_x, float(max_x)))
        self.pos_y = max(0.0, min(self.pos_y, float(max_y)))
        self.rect.topleft = (int(self.pos_x), int(self.pos_y))

class Planta:
    """Entidad estatica que sirve de alimento para los peces."""

    def __init__(self, nombre, energia):
        """Ubica la planta en coordenadas aleatorias dentro de la pantalla."""
        self.nombre = nombre
        self.energia = energia
        self.rect = pygame.Rect(
            random.randint(0, max(0, WIDTH - 14)),
            random.randint(0, max(0, HEIGHT - 14)),
            14,
            14,
        )

class Pez(Animal):
    """Herbivoro basico: come plantas y huye de depredadores ligeros."""

    def __init__(self, nombre, energia, tiempo_vida):
        """Inicializa el pez con tamaño especifico y velocidad reducida."""
        super().__init__(nombre, energia, tiempo_vida, ancho=20, alto=20)
        # --- CAMBIO: Velocidad reducida para 60 FPS ---
        self.velocidad_frame = random.uniform(1.0, 2.0) # Era 2.0 a 4.0

    def comer(self, planta):
        """Consume plantas y devuelve la energia obtenida."""
        if isinstance(planta, Planta):
            self.energia += planta.energia
            return planta.energia
        return 0

    def reproducir(self):
        """Genera una nueva cria si tiene energia y edad suficientes."""
        if self.energia > 100 and self.edad > 5 and random.random() < 0.1:
            self.energia -= 50  # Reproducirse cuesta energía para evitar explosión poblacional.
            cria = Pez("Pejerrey", 50, 20)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

    def decidir_objetivo(self, listas_de_seres):
        """Huya de depredadores cercanos o busca plantas si tiene hambre."""
        lista_depredadores = listas_de_seres["truchas"] + listas_de_seres["tiburones"]
        lista_de_plantas = listas_de_seres["plantas"]
        rango_vision_depredador = 150 * 150
        rango_vision_planta = 100 * 100
        depredador_cercano = None
        planta_cercana = None
        dist_min_depredador = rango_vision_depredador
        dist_min_planta = rango_vision_planta
        for dep in lista_depredadores:
            # Se usa distancia al cuadrado para evitar sqrt.
            distancia = (self.rect.centerx - dep.rect.centerx) ** 2 + (self.rect.centery - dep.rect.centery) ** 2
            if distancia < dist_min_depredador:
                dist_min_depredador = distancia
                depredador_cercano = dep
        if self.energia < 70:
            for planta in lista_de_plantas:
                # Solo busca comida cuando realmente tiene hambre.
                distancia = (self.rect.centerx - planta.rect.centerx) ** 2 + (self.rect.centery - planta.rect.centery) ** 2
                if distancia < dist_min_planta:
                    dist_min_planta = distancia
                    planta_cercana = planta
        if depredador_cercano:
            # Se aleja 70 px en cada eje para salir del radio inmediato.
            if self.rect.centerx < depredador_cercano.rect.centerx: self.target_x = self.rect.x - 70
            else: self.target_x = self.rect.x + 70
            if self.rect.centery < depredador_cercano.rect.centery: self.target_y = self.rect.y - 70
            else: self.target_y = self.rect.y + 70
        elif self.energia < 70 and planta_cercana:
            self.target_x = float(planta_cercana.rect.centerx)
            self.target_y = float(planta_cercana.rect.centery)
        
        # --- SOLUCIÓN TIRONES (IDEA 2) ---
        # La lógica de "vagar" ahora está en update_movimiento_frame,
        # así que la quitamos de aquí para evitar conflictos.
        
        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Carnivoro(Animal):
    """Especializacion de Animal que caza una lista concreta de presas."""

    def __init__(self, nombre, energia, tiempo_vida, presa_key, hambre_threshold, ancho=12, alto=12):
        """Almacena el tipo de presa y el umbral a partir del cual caza."""
        super().__init__(nombre, energia, tiempo_vida, ancho=ancho, alto=alto)
        self.presa_key = presa_key
        self.hambre_threshold = hambre_threshold
        self.presa_objetivo = None
        
    def decidir_objetivo(self, listas_de_seres):
        """Busca la presa mas cercana solo cuando el hambre supera el umbral."""
        lista_de_presas = listas_de_seres[self.presa_key]
        self.presa_objetivo = None
        presa_cercana = None
        distancia_minima = float('inf')
        if self.energia < self.hambre_threshold:
            for presa in lista_de_presas:
                distancia = (self.rect.centerx - presa.rect.centerx) ** 2 + (self.rect.centery - presa.rect.centery) ** 2
                if distancia < distancia_minima:
                    distancia_minima = distancia
                    presa_cercana = presa
        if presa_cercana:
            self.presa_objetivo = presa_cercana
            self.target_x = float(presa_cercana.rect.centerx)
            self.target_y = float(presa_cercana.rect.centery)
        # --- SOLUCIÓN TIRONES (IDEA 2) ---
        # La lógica de "vagar" ahora está en update_movimiento_frame
            
        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Trucha(Carnivoro):
    """Especie intermedia: caza peces pero puede huir de tiburones."""

    def __init__(self, nombre, energia, tiempo_vida):
        """Configura el tamaño mayor y el umbral de hambre de la trucha."""
        super().__init__(nombre, energia, tiempo_vida, presa_key="peces", hambre_threshold=80, ancho=35, alto=35)
        # --- CAMBIO: Velocidad reducida para 60 FPS ---
        self.velocidad_frame = random.uniform(0.75, 1.75) # Era 1.5 a 3.5
        
    # --- ¡NUEVO! IA DE FUGA (Req 4) ---
    def decidir_objetivo(self, listas_de_seres):
        """Sobrescribe el método de Carnivoro para añadir lógica de fuga."""
        lista_depredadores = listas_de_seres["tiburones"]
        rango_vision_depredador = 150 * 150 # Igual que el pez
        depredador_cercano = None
        dist_min_depredador = rango_vision_depredador

        # 1. Buscar depredadores (Tiburones)
        for dep in lista_depredadores:
            # Se queda con el tiburon más cercano para decidir si huir.
            distancia = (self.rect.centerx - dep.rect.centerx) ** 2 + (self.rect.centery - dep.rect.centery) ** 2
            if distancia < dist_min_depredador:
                dist_min_depredador = distancia
                depredador_cercano = dep
        
        # 2. Decidir: ¿Huir o Cazar?
        if depredador_cercano:
            # ¡Huir!
            if self.rect.centerx < depredador_cercano.rect.centerx: self.target_x = self.rect.x - 70
            else: self.target_x = self.rect.x + 70
            if self.rect.centery < depredador_cercano.rect.centery: self.target_y = self.rect.y - 70
            else: self.target_y = self.rect.y + 70
        else:
            # No hay peligro, cazar (lógica original de Carnivoro)
            super().decidir_objetivo(listas_de_seres)
            
        # Limitar a la pantalla
        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

    def comer(self, pez):
        """Absorbe energia de la presa capturada."""
        if isinstance(pez, Pez):
            energia_ganada = pez.energia // 2
            self.energia += energia_ganada
            return energia_ganada
        return 0
    def reproducir(self):
        """Crea una nueva trucha si supera los requisitos."""
        if self.energia > 150 and self.edad > 8 and random.random() < 0.05:
            self.energia -= 70  # Coste mas alto para especies de mayor nivel.
            cria = Trucha("Trucha", 100, 25)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Tiburon(Carnivoro):
    """Depredador alfa que persigue truchas con movimiento guiado."""

    def __init__(self, nombre, energia, tiempo_vida):
        """Define la fuerza, tamaño y estado interno del tiburon."""
        super().__init__(nombre, energia, tiempo_vida, presa_key="truchas", hambre_threshold=150, ancho=45, alto=45)
        # --- CAMBIO (Req 3): Tiburones más lentos y 60 FPS ---
        self.velocidad_frame = random.uniform(0.4, 1.2) # Era 1.0 a 3.0 (reducido a la mitad) y luego 0.5 a 1.5
        self.estado = 'vagando'  # Se usa para alternar entre persecucion guiada y desplazamiento libre.

    def decidir_objetivo(self, listas_de_seres):
        """Aplica la logica generica y marca si esta cazando o vagando."""
        super().decidir_objetivo(listas_de_seres)
        self.estado = 'cazando' if self.presa_objetivo else 'vagando'

    def update_movimiento_frame(self):
        """Recalcula el objetivo cada frame para simular persecucion constante."""
        if self.estado == 'cazando' and self.presa_objetivo:
            presa_rect = getattr(self.presa_objetivo, 'rect', None)
            if presa_rect:
                # Mantiene el blanco actualizado cada frame para simular persecución guiada.
                self.target_x = float(presa_rect.centerx)
                self.target_y = float(presa_rect.centery)
        super().update_movimiento_frame()
        
    def comer(self, trucha):
        """Consume una trucha y libera el objetivo actual."""
        if isinstance(trucha, Trucha):
            energia_ganada = trucha.energia // 2
            self.energia += energia_ganada
            self.presa_objetivo = None  # Se reinicia el estado para que vuelva a vagar.
            self.estado = 'vagando'
            return energia_ganada
        return 0

    def reproducir(self):
        """Crea una nueva cría si alcanza los altos costos energéticos."""
        if self.energia > 200 and self.edad > 10 and random.random() < 0.03:
            self.energia -= 100  # Los depredadores tope requieren mucha energia para criar.
            cria = Tiburon("Tiburón", 200, 30)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Ecosistema:
    """Orquesta las listas de entidades y aplica las reglas de interaccion."""

    def __init__(self):
        """Crea contenedores vacios y almacena eventos para la vista."""
        self.peces = []          # Lista de Pez
        self.truchas = []        # Lista de Trucha
        self.tiburones = []      # Lista de Tiburon
        self.plantas = []        # Lista de Planta
        self.eventos_visuales = []  # La vista leerá estos eventos luego de cada turno.

    def poblar_inicial(self):
        """Atajo para poblar con los valores por defecto."""
        self.poblar_custom()

    def poblar_custom(self, n_plantas=25, n_peces=15, n_truchas=5, n_tiburones=2):
        """Permite poblar con cantidades personalizadas por especie."""
        self.plantas = [Planta("Alga", 20) for _ in range(n_plantas)]
        self.peces = [Pez("Pejerrey", 70, 120) for _ in range(n_peces)]
        self.truchas = [Trucha("Trucha", 120, 180) for _ in range(n_truchas)]
        self.tiburones = [Tiburon("Tiburon", 200, 30) for _ in range(n_tiburones)]
        
    def simular_turno_ia(self):
        """Ejecuta un 'tick' de IA: comer, morir y reproducirse."""
        self.eventos_visuales.clear()
        
        peces_muertos, truchas_muertas, tiburones_muertos = [], [], []
        plantas_comidas = []
        nuevas_crias_peces, nuevas_crias_truchas, nuevas_crias_tiburones = [], [], []

        listas_de_seres = {
            "peces": self.peces,
            "truchas": self.truchas,
            "tiburones": self.tiburones,
            "plantas": self.plantas
        }
        # La estructura anterior facilita pasar referencias a cada método decidir_objetivo.

        # Peces: comen plantas, pueden reproducirse y morir
        for pez in self.peces:
            pez.update_decision_turno(listas_de_seres)  # Selecciona nuevo objetivo según hambre/peligro.
            for planta in self.plantas:
                if pez.rect.colliderect(planta.rect) and planta not in plantas_comidas:
                    energia_ganada = pez.comer(planta)
                    if energia_ganada > 0:
                        self.eventos_visuales.append(('comer_pez', pez.rect.center, energia_ganada))
                    plantas_comidas.append(planta)
                    break
            cria = pez.reproducir()
            if cria:
                nuevas_crias_peces.append(cria)  # Se agregan luego para evitar modificar lista en iteración.
                self.eventos_visuales.append(('nacer', cria.rect.center))
            if pez.ha_muerto():
                peces_muertos.append(pez)
                self.eventos_visuales.append(('morir', pez.rect.center))

        # Truchas: cazan peces y aplican su propia logica de fuga
        for trucha in self.truchas:
            trucha.update_decision_turno(listas_de_seres)
            for pez in self.peces:
                # Se omiten peces ya marcados como muertos para evitar consumirlos dos veces.
                if pez not in peces_muertos and trucha.rect.colliderect(pez.rect):
                    energia_ganada = trucha.comer(pez)
                    if energia_ganada > 0:
                        self.eventos_visuales.append(('comer_depredador', trucha.rect.center, energia_ganada))
                    if pez not in peces_muertos:
                        peces_muertos.append(pez)
                        self.eventos_visuales.append(('morir', pez.rect.center))
                    break
            cria = trucha.reproducir()
            if cria:
                nuevas_crias_truchas.append(cria)
                self.eventos_visuales.append(('nacer', cria.rect.center))
            if trucha.ha_muerto():
                truchas_muertas.append(trucha)
                self.eventos_visuales.append(('morir', trucha.rect.center))

        # Tiburones: cazan truchas y son la cima de la cadena
        for tiburon in self.tiburones:
            tiburon.update_decision_turno(listas_de_seres)
            for trucha in self.truchas:
                if trucha not in truchas_muertas and tiburon.rect.colliderect(trucha.rect):
                    energia_ganada = tiburon.comer(trucha)
                    if energia_ganada > 0:
                        self.eventos_visuales.append(('comer_depredador', tiburon.rect.center, energia_ganada))
                    if trucha not in truchas_muertas:
                        truchas_muertas.append(trucha)
                        self.eventos_visuales.append(('morir', trucha.rect.center))
                    break
            cria = tiburon.reproducir()
            if cria:
                nuevas_crias_tiburones.append(cria)
                self.eventos_visuales.append(('nacer', cria.rect.center))
            if tiburon.ha_muerto():
                tiburones_muertos.append(tiburon)
                self.eventos_visuales.append(('morir', tiburon.rect.center))

        # Limpieza de listas para remover los elementos marcados
        set_peces_muertos = set(peces_muertos)
        set_truchas_muertas = set(truchas_muertas)
        set_tiburones_muertos = set(tiburones_muertos)
        set_plantas_comidas = set(plantas_comidas)

        # Las listas se reconstruyen excluyendo elementos marcados para mantener consistencia.
        self.peces = [p for p in self.peces if p not in set_peces_muertos]
        self.truchas = [t for t in self.truchas if t not in set_truchas_muertas]
        self.tiburones = [t for t in self.tiburones if t not in set_tiburones_muertos]
        self.plantas = [p for p in self.plantas if p not in set_plantas_comidas]

        # Adición de nuevas crías
        self.peces.extend(nuevas_crias_peces)
        self.truchas.extend(nuevas_crias_truchas)
        self.tiburones.extend(nuevas_crias_tiburones)

        if random.random() < 0.8:
            # Regeneracion simple de algas para mantener alimento disponible.
            self.plantas.append(Planta("Alga", 20))
            
    def get_all_entities(self):
        """Devuelve todas las listas de entidades para la Vista."""
        return self.plantas, self.peces, self.truchas, self.tiburones

    def actualizar_movimiento_frame(self):
        """Actualiza el movimiento continuo de todas las criaturas."""
        todos_los_animales = self.peces + self.truchas + self.tiburones  # Plantas no se mueven.
        for animal in todos_los_animales:
            animal.update_movimiento_frame()
            

