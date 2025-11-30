import pygame
import random
import math
from abc import ABC, abstractmethod # Usamos ABC para definir 'interfaces'
from pygame import Color 

"""Define la logica central y describe las reglas de comportamiento del ecosistema."""

# El módulo expone tanto el modelo como los valores compartidos con la vista,
# de modo que se mantiene una única fuente de verdad para tamaños y colores.

# ---------------------------------
# CONFIGURACIÓN GLOBAL (compartida)
# ---------------------------------
# "Definimos las constantes aquí. Si queremos cambiar la velocidad de la IA
# o la resolución, lo hacemos en UN solo lugar."
WIDTH, HEIGHT = 1024, 768      # Resolucion base de la ventana (vista reutiliza).
FPS = 60                       # Se subio a 60 para dar mas suavidad visual.
TURNO_DURACION_MS = 1000       # Cada segundo se ejecuta un turno discreto de IA.
GRID_CELDA = 64                

# Parámetros del ciclo día/noche (controlan el reloj interno del ecosistema)
CICLO_DIA_TURNOS = 32          # Cantidad de turnos de IA que dura un día completo.
FRACCION_AMANECER = 0.18       # Porción inicial dedicada al amanecer.
FRACCION_ATARDECER = 0.68      # Punto a partir del cual el cielo se vuelve nocturno.

# Rango permitido por especie para evitar extinciones o sobrepoblación
POBLACION_LIMITES = {
    "plantas": {"min": 20, "max": 70},
    "peces": {"min": 12, "max": 40},
    "truchas": {"min": 5, "max": 18},
    "tiburones": {"min": 2, "max": 10},
}

# Colores (usados por la Vista, pero importados desde aquí)
# "La Lógica define los colores. La Vista solo los usa para pintar."
BLANCO = Color(255, 255, 255)
AZUL = Color(0, 0, 255)
VERDE = Color(0, 255, 0)
MARRON = Color(139, 69, 19)
GRIS = Color(169, 169, 169)

# Configuración de texturas
# "La lógica define QUÉ texturas usar (por clave), la vista decide CÓMO cargarlas."
TEXTURAS = {
    'pez': ['pez.png', 'pez.gif', 'fish.png'],
    'trucha': ['trucha.png', 'trucha.gif'],
    'tiburon': ['tiburon.png', 'tiburon.gif', 'shark.png'],
    'alga': ['algagif.gif', 'alga.png', 'alga.gif'],
}

# Tamaños visuales de cada entidad
# "Definimos el 'hitbox' o tamaño de la entidad aquí, en el modelo."
TEXTURAS_TAM = {
    'pez': (20, 20),
    'trucha': (35, 35),
    'tiburon': (45, 45),
    'alga': (14, 14),
}

# --- Colores para la VISTA (UI y Fondo) ---
# "Incluso los colores de la UI se definen aquí, permitiendo 'theming'
# centralizado si quisiéramos."
AGUA_CLARA = Color(173, 216, 230)
AGUA_OSCURA = Color(0, 105, 148)
NEGRO_UI = Color(20, 20, 20) 

# --- Colores para BOTONES ---
COLOR_TEXTO_BTN = Color(255, 255, 255)
COLOR_START = Color(40, 167, 69)
COLOR_STOP = Color(220, 53, 69)
COLOR_PAUSE = Color(255, 193, 7)
COLOR_RESUME = Color(23, 162, 184)

# --- Colores para Partículas de Eventos ---
COLOR_COMER = Color(144, 238, 144) 
COLOR_NACER = Color(255, 182, 193) 
COLOR_MORIR = Color(160, 160, 160) 
COLOR_BURBUJA = Color(200, 225, 255)

# --- NUEVOS COLORES PARA EL PANEL LATERAL ---
COLOR_PANEL_FONDO = Color(33, 37, 41, 230) 
COLOR_TEXTO_TITULO = Color(248, 249, 250) 
COLOR_TEXTO_NORMAL = Color(206, 212, 218) 
COLOR_BARRA_FONDO = Color(73, 80, 87)
COLOR_BARRA_PROGRESO = Color(0, 123, 255) 
COLOR_SEPARADOR = Color(108, 117, 125) 


# ---------------------------------
# CAPA DE LÓGICA (MODELO)
# ---------------------------------

# "Esta es nuestra 'Clase Base Abstracta'. Es el contrato que
# todo animal debe cumplir. Define el 'qué' pero no el 'cómo'."
class Animal(ABC):
    """Modelo base para cualquier criatura con energia, edad y posicion."""

    def __init__(self, nombre, energia, tiempo_vida, ancho=10, alto=10):
        """Genera una entidad con posicion aleatoria y estados iniciales."""
        self.nombre = nombre
        self.energia = energia
        self.tiempo_vida = tiempo_vida
        self.edad = 0
        
        # "El 'rect' es la posición oficial en el mundo, en píxeles enteros."
        self.rect = pygame.Rect(
            random.randint(0, max(0, WIDTH - ancho)),
            random.randint(0, max(0, HEIGHT - alto)),
            ancho,
            alto,
        )
        # "PERO, usamos floats para la posición y el objetivo. Esto es clave
        # para el movimiento suave (interpolación)."
        self.target_x = float(self.rect.x) # El destino (discreto)
        self.target_y = float(self.rect.y)
        
        self.velocidad_frame = random.uniform(0.5, 1.5) 
        self.velocidad_base = self.velocidad_frame

        self.pos_x = float(self.rect.x)  # La posición actual (continua)
        self.pos_y = float(self.rect.y)
        
        self.direccion_h = 1 # 1 = derecha, -1 = izquierda (para la Vista)
        self.estado_tiempo = None
        self.consumo_base = 2.0
        
        # ... (recortes de seguridad) ...
        if self.rect.right > WIDTH: self.rect.right = WIDTH
        if self.rect.bottom > HEIGHT: self.rect.bottom = HEIGHT
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.target_x, self.target_y = self.pos_x, self.pos_y

    # "Estos métodos abstractos FUERZAN a las clases hijas (Pez, Trucha)
    # a implementar su propia lógica."
    @abstractmethod
    def decidir_objetivo(self, listas_de_seres):
        """Define la IA concreta de cada especie al elegir su destino."""

    @abstractmethod
    def comer(self, objetivo):
        """Resuelve como aumenta energia cuando la especie come algo."""

    @abstractmethod
    def reproducir(self, estado_tiempo):
        """Devuelve una nueva cría (si aplica) usando el contexto del ciclo."""

    def update_decision_turno(self, listas_de_seres):
        """Actualiza energia/edad y delega la seleccion de objetivos."""
        # "Este es el 'tick' de IA (lento). Consume energía y envejece."
        self.energia -= self.consumo_base
        self.edad += 1     
        self.estado_tiempo = listas_de_seres.get("estado_tiempo")
        self.decidir_objetivo(listas_de_seres) # "Aquí el animal 'piensa'."

    def update_movimiento_frame(self):
        """Interpolacion suave hacia el objetivo elegido en el turno de IA."""
        # "Este es el 'tick' de render (rápido). Solo mueve el sprite
        # un poquito hacia el 'target_x'/'target_y' que decidió la IA."
        
        self._limitar_objetivo_a_pantalla()
        dist_x = abs(self.target_x - self.pos_x)
        dist_y = abs(self.target_y - self.pos_y)
        
        # "Si el animal llega a su destino (un umbral de 5px)..."
        if dist_x < 5 and dist_y < 5:
            # "...no se queda quieto 'tiritando'. Le damos un nuevo
            # objetivo de 'vagar' cercano. Esto da fluidez."
            self.target_x = self.pos_x + random.randint(-50, 50)
            self.target_y = self.pos_y + random.randint(-50, 50)
            self._limitar_objetivo_a_pantalla()

        # "Esta es la interpolación lineal (Lerp) simple."
        dx = self.target_x - self.pos_x 
        dy = self.target_y - self.pos_y 
        
        if abs(dx) > 0.1: 
            # "Calcula el paso, limitado por la velocidad del animal."
            step_x = max(-self.velocidad_frame, min(self.velocidad_frame, dx))
            self.pos_x += step_x
            self.direccion_h = 1 if step_x > 0 else -1 # "Informa a la Vista si mira izq/der"
        
        if abs(dy) > 0:
            step_y = max(-self.velocidad_frame, min(self.velocidad_frame, dy))
            self.pos_y += step_y
            
        self._limitar_posicion_a_pantalla()

    def ha_muerto(self):
        """Evalua si el animal llego a su limite de vida o energia."""
        return self.edad >= self.tiempo_vida or self.energia <= 0

    # "Estos son métodos de utilidad ('helpers') privados. Encapsulan
    # la lógica de 'mantenerse dentro de la pantalla'."
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
        # "Al final, actualiza el 'rect' entero, que es lo que la Vista dibujará."
        self.rect.topleft = (int(self.pos_x), int(self.pos_y))

class Planta:
    """Entidad estatica que sirve de alimento para los peces."""
    # "Esta clase es simple a propósito. No hereda de 'Animal'
    # porque no se mueve, no envejece, no tiene IA."
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
        self.velocidad_frame = random.uniform(1.0, 2.0) 
        self.velocidad_base = self.velocidad_frame
        self.consumo_base = 1.0

    def comer(self, planta):
        """Consume plantas y devuelve la energia obtenida."""
        if isinstance(planta, Planta):
            self.energia += planta.energia
            return planta.energia
        return 0

    def reproducir(self, estado_tiempo):
        """Genera una nueva cria si tiene energia y edad suficientes."""
        # "Reglas de negocio: la probabilidad aumenta al amanecer y se detiene de noche."
        fase = estado_tiempo.get("fase") if estado_tiempo else None
        if fase == "noche":
            prob_base = 0.08
        else:
            prob_base = 0.18
        if fase == "amanecer":
            prob_base += 0.06
        elif fase == "atardecer":
            prob_base += 0.03
        energia_umbral = 60 if fase in ("amanecer", "atardecer") else 70
        if self.energia > energia_umbral and self.edad > 3 and random.random() < prob_base:
            self.energia -= 50  # Coste para evitar explosión poblacional.
            cria = Pez("Pejerrey", 50, 20)
            cria.rect.topleft = self.rect.topleft # "La cría aparece donde el padre."
            return cria
        return None

    def decidir_objetivo(self, listas_de_seres):
        """Huya de depredadores cercanos o busca plantas si tiene hambre."""
        # "Aquí está la IA del Pez:
        # 1. ¿Hay depredadores?
        # 2. Si no, ¿tengo hambre?
        # 3. Si no, 'vagar' (manejado por la clase base)."
        lista_depredadores = listas_de_seres["truchas"] + listas_de_seres["tiburones"]
        lista_de_plantas = listas_de_seres["plantas"]
        rango_vision_depredador = 150 * 150 # "Usamos distancia al cuadrado. Es una
        rango_vision_planta = 100 * 100     # optimización: evitamos 'sqrt' (raíz cuadrada)."
        estado_tiempo = self.estado_tiempo or {}
        es_noche = estado_tiempo.get("es_noche", False)
        if es_noche:
            rango_vision_planta = 80 * 80  # Se reduce la visibilidad con poca luz.
        depredador_cercano = None
        planta_cercana = None
        dist_min_depredador = rango_vision_depredador
        dist_min_planta = rango_vision_planta
        
        # "1. Evaluar peligro."
        for dep in lista_depredadores:
            distancia = (self.rect.centerx - dep.rect.centerx) ** 2 + (self.rect.centery - dep.rect.centery) ** 2
            if distancia < dist_min_depredador:
                dist_min_depredador = distancia
                depredador_cercano = dep
        
        # "2. Evaluar hambre (solo si no hay peligro)."
        if self.energia < 70:
            for planta in lista_de_plantas:
                distancia = (self.rect.centerx - planta.rect.centerx) ** 2 + (self.rect.centery - planta.rect.centery) ** 2
                if distancia < dist_min_planta:
                    dist_min_planta = distancia
                    planta_cercana = planta
        
        # "3. Tomar decisión."
        if depredador_cercano:
            # "Lógica de huida: calcula un vector opuesto."
            if self.rect.centerx < depredador_cercano.rect.centerx: self.target_x = self.rect.x - 70
            else: self.target_x = self.rect.x + 70
            if self.rect.centery < depredador_cercano.rect.centery: self.target_y = self.rect.y - 70
            else: self.target_y = self.rect.y + 70
        elif es_noche and self.energia > 40:
            # "Por la noche se refugia en zonas profundas en lugar de exponerse."
            self.target_x = float(self.rect.x + random.randint(-30, 30))
            self.target_y = float(min(HEIGHT - self.rect.height, self.rect.y + 60))
        elif (self.energia < 70 or (es_noche and self.energia < 40)) and planta_cercana:
            # "Lógica de caza (plantas): ir hacia el objetivo."
            self.target_x = float(planta_cercana.rect.centerx)
            self.target_y = float(planta_cercana.rect.centery)

        # "El 'vagar' (si no pasa nada) se maneja en update_movimiento_frame."
        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Carnivoro(Animal):
    """Especializacion de Animal que caza una lista concreta de presas."""
    # "Esta es otra clase base. Abstrae la lógica de 'cazar'.
    # Fíjense cómo 'presa_key' permite reutilizar esto para Truchas y Tiburones."
    def __init__(self, nombre, energia, tiempo_vida, presa_key, hambre_threshold, ancho=12, alto=12):
        """Almacena el tipo de presa y el umbral a partir del cual caza."""
        super().__init__(nombre, energia, tiempo_vida, ancho=ancho, alto=alto)
        self.presa_key = presa_key # "Ej: 'peces' o 'truchas'"
        self.hambre_threshold = hambre_threshold
        self.presa_objetivo = None # "Guarda el objetivo actual."
        
    def decidir_objetivo(self, listas_de_seres):
        """Busca la presa mas cercana solo cuando el hambre supera el umbral."""
        lista_de_presas = listas_de_seres[self.presa_key]
        self.presa_objetivo = None
        presa_cercana = None
        distancia_minima = float('inf')
        estado_tiempo = self.estado_tiempo or {}
        es_noche = estado_tiempo.get("es_noche", False)
        fase = estado_tiempo.get("fase")
        hambre_tolerada = self.hambre_threshold
        if es_noche:
            hambre_tolerada *= 1.2  # Los depredadores se activan más en la oscuridad.
        elif fase == "dia":
            hambre_tolerada *= 0.9  # Con abundante luz son más cautos.
        busca_presa = self.energia < hambre_tolerada or (es_noche and random.random() < 0.35)
        
        # "Solo busca presas si tiene hambre."
        if busca_presa:
            for presa in lista_de_presas:
                distancia = (self.rect.centerx - presa.rect.centerx) ** 2 + (self.rect.centery - presa.rect.centery) ** 2
                if distancia < distancia_minima:
                    distancia_minima = distancia
                    presa_cercana = presa
        
        if presa_cercana:
            # "Fija el objetivo."
            self.presa_objetivo = presa_cercana
            self.target_x = float(presa_cercana.rect.centerx)
            self.target_y = float(presa_cercana.rect.centery)

        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Trucha(Carnivoro):
    """Especie intermedia: caza peces pero puede huir de tiburones."""

    def __init__(self, nombre, energia, tiempo_vida):
        """Configura el tamaño mayor y el umbral de hambre de la trucha."""
        # "Llama al 'super' de Carnivoro, especializándolo."
        super().__init__(nombre, energia, tiempo_vida, presa_key="peces", hambre_threshold=80, ancho=35, alto=35)
        self.velocidad_frame = random.uniform(0.75, 1.75) 
        self.consumo_base = 1.5
        
    def decidir_objetivo(self, listas_de_seres):
        """Sobrescribe el método de Carnivoro para añadir lógica de fuga."""
        # "Esto es Polimorfismo en acción.
        # La Trucha REESCRIBE la IA de 'Carnivoro'."
        lista_depredadores = listas_de_seres["tiburones"]
        rango_vision_depredador = 150 * 150 
        depredador_cercano = None
        dist_min_depredador = rango_vision_depredador
        estado_tiempo = self.estado_tiempo or {}
        es_noche = estado_tiempo.get("es_noche", False)
        fase = estado_tiempo.get("fase")

        # "1. Buscar depredadores (Tiburones) - PRIORIDAD MÁXIMA."
        for dep in lista_depredadores:
            distancia = (self.rect.centerx - dep.rect.centerx) ** 2 + (self.rect.centery - dep.rect.centery) ** 2
            if distancia < dist_min_depredador:
                dist_min_depredador = distancia
                depredador_cercano = dep
        
        # "2. Decidir: ¿Huir o Cazar?"
        if depredador_cercano:
            # "¡Huir! (Lógica copiada del Pez)"
            if self.rect.centerx < depredador_cercano.rect.centerx: self.target_x = self.rect.x - 70
            else: self.target_x = self.rect.x + 70
            if self.rect.centery < depredador_cercano.rect.centery: self.target_y = self.rect.y - 70
            else: self.target_y = self.rect.y + 70
        else:
            # "No hay peligro. Ahora sí, ejecutamos la lógica de caza
            # que heredamos de Carnivoro."
            super().decidir_objetivo(listas_de_seres)
            if not self.presa_objetivo:
                if es_noche:
                    # "Por la noche patrullan el fondo y reducen velocidad vertical."
                    self.target_y = float(min(HEIGHT - self.rect.height, self.rect.y + 30))
                elif fase == "amanecer":
                    # "Al amanecer tienden a subir a zonas iluminadas."
                    self.target_y = float(max(0, self.rect.y - 50))
            
        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

    def comer(self, pez):
        """Absorbe energia de la presa capturada."""
        if isinstance(pez, Pez):
            energia_ganada = max(35, pez.energia // 2)
            self.energia += energia_ganada
            return energia_ganada
        return 0
    
    def reproducir(self, estado_tiempo):
        """Crea una nueva trucha si supera los requisitos."""
        prob = 0.1
        fase = estado_tiempo.get("fase") if estado_tiempo else None
        if fase == "noche":
            prob *= 0.7
        elif fase in ("amanecer", "atardecer"):
            prob += 0.05
        energia_umbral = 110 if fase in ("amanecer", "atardecer") else 120
        if self.energia > energia_umbral and self.edad > 6 and random.random() < prob:
            self.energia -= 70 
            cria = Trucha("Trucha", 100, 25)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Tiburon(Carnivoro):
    """Depredador alfa que persigue truchas con movimiento guiado."""

    def __init__(self, nombre, energia, tiempo_vida):
        """Define la fuerza, tamaño y estado interno del tiburon."""
        super().__init__(nombre, energia, tiempo_vida, presa_key="truchas", hambre_threshold=120, ancho=45, alto=45)
        self.velocidad_frame = random.uniform(0.4, 1.2) 
        self.velocidad_base = self.velocidad_frame
        self.consumo_base = 0.8
        self.estado = 'vagando'  # "El Tiburón tiene un estado interno simple."
        self.presa_secundaria = "peces"

    def decidir_objetivo(self, listas_de_seres):
        """Aplica la logica generica y marca si esta cazando o vagando."""
        # "Solo llama al 'super' y actualiza su estado."
        super().decidir_objetivo(listas_de_seres)
        if not self.presa_objetivo and self.presa_secundaria:
            lista_alt = listas_de_seres.get(self.presa_secundaria, [])
            presa_alt = None
            distancia_minima = float('inf')
            for presa in lista_alt:
                distancia = (self.rect.centerx - presa.rect.centerx) ** 2 + (self.rect.centery - presa.rect.centery) ** 2
                if distancia < distancia_minima:
                    distancia_minima = distancia
                    presa_alt = presa
            if presa_alt:
                self.presa_objetivo = presa_alt
                self.target_x = float(presa_alt.rect.centerx)
                self.target_y = float(presa_alt.rect.centery)
        self.estado = 'cazando' if self.presa_objetivo else 'vagando'

    def update_movimiento_frame(self):
        """Recalcula el objetivo cada frame para simular persecucion constante."""
        # "Esta es la IA especial del Tiburón.
        # Sobrescribe el movimiento, no la decisión."
        estado_tiempo = self.estado_tiempo or {}
        if estado_tiempo:
            if estado_tiempo.get("es_noche"):
                self.velocidad_frame = min(2.0, self.velocidad_base * 1.25)
            elif estado_tiempo.get("fase") == "amanecer":
                self.velocidad_frame = min(2.0, self.velocidad_base * 1.1)
            else:
                self.velocidad_frame = max(0.3, self.velocidad_base * 0.9)
        if self.estado == 'cazando' and self.presa_objetivo:
            presa_rect = getattr(self.presa_objetivo, 'rect', None)
            if presa_rect:
                # "En CADA FRAME (60/s), recalcula el objetivo.
                # Esto es 'Homing' (persecución), no 'Interpolación' (ir a un punto fijo)."
                self.target_x = float(presa_rect.centerx)
                self.target_y = float(presa_rect.centery)
        
        # "Y después de ajustar el objetivo, llama al 'super' para
        # que ejecute el movimiento de interpolación normal."
        super().update_movimiento_frame()
        
    def comer(self, trucha):
        """Consume una trucha y libera el objetivo actual."""
        if isinstance(trucha, Trucha):
            energia_ganada = max(85, int(trucha.energia * 0.7))
            self.energia += energia_ganada
            self.presa_objetivo = None  # "Importante: suelta el objetivo."
            self.estado = 'vagando'
            return energia_ganada
        if isinstance(trucha, Pez):
            energia_ganada = max(40, int(trucha.energia * 0.6))
            self.energia += energia_ganada
            self.presa_objetivo = None
            self.estado = 'vagando'
            return energia_ganada
        return 0

    def reproducir(self, estado_tiempo):
        """Crea una nueva cría si alcanza los altos costos energéticos."""
        prob = 0.1
        fase = estado_tiempo.get("fase") if estado_tiempo else None
        if estado_tiempo and estado_tiempo.get("es_noche"):
            prob = 0.15
        elif fase == "amanecer":
            prob = 0.12
        energia_umbral = 150 if (fase in ("amanecer", "atardecer")) else 170
        if self.energia > energia_umbral and self.edad > 8 and random.random() < prob:
            self.energia -= 100 
            cria = Tiburon("Tiburón", 200, 30)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

# "Finalmente, la clase 'Ecosistema'. Este es el objeto 'Modelo'
# que 'main.py' instancia. Contiene todas las listas."
class Ecosistema:
    """Orquesta las listas de entidades y aplica las reglas de interaccion."""

    def __init__(self):
        """Crea contenedores vacios y almacena eventos para la vista."""
        self.peces = []
        self.truchas = []
        self.tiburones = []
        self.plantas = []
        self.turno_global = 0
        self.estado_tiempo = {}
        
        # "Esta es la COLA DE COMUNICACIÓN.
        # Cuando la lógica mata un pez, añade un 'evento' aquí.
        # La Vista lo leerá y dibujará la '💀'."
        self.eventos_visuales = []
        self._actualizar_estado_tiempo(avanzar=False)

    def poblar_inicial(self):
        """Atajo para poblar con los valores por defecto."""
        self.poblar_custom()

    def poblar_custom(self, n_plantas=25, n_peces=15, n_truchas=5, n_tiburones=2):
        """Permite poblar con cantidades personalizadas por especie."""
        # "Este es el método que 'main' usa al pulsar 'Start'."
        self.plantas = [Planta("Alga", 20) for _ in range(n_plantas)]
        self.peces = [Pez("Pejerrey", 70, 120) for _ in range(n_peces)]
        self.truchas = [Trucha("Trucha", 120, 180) for _ in range(n_truchas)]
        self.tiburones = [Tiburon("Tiburon", 200, 30) for _ in range(n_tiburones)]
        self.turno_global = 0
        self._actualizar_estado_tiempo(avanzar=False)
        self._balancear_poblaciones()

    def _fase_por_progreso(self, progreso):
        """Determina la fase (amanecer/día/atardecer/noche) a partir del avance normalizado."""
        if progreso < FRACCION_AMANECER:
            return "amanecer"
        if progreso < 0.5:
            return "dia"
        if progreso < FRACCION_ATARDECER:
            return "atardecer"
        return "noche"

    def _actualizar_estado_tiempo(self, avanzar=True):
        """Avanza el reloj discreto y recalcula los valores expuestos a la Vista."""
        if avanzar:
            self.turno_global += 1
        ciclo_turno = self.turno_global % CICLO_DIA_TURNOS
        progreso = ciclo_turno / float(CICLO_DIA_TURNOS)
        fase = self._fase_por_progreso(progreso)
        dia = (self.turno_global // CICLO_DIA_TURNOS) + 1
        factor_luz = 0.5 - 0.5 * math.cos(2 * math.pi * progreso)
        self.estado_tiempo = {
            "turno": self.turno_global,
            "dia": dia,
            "progreso_dia": progreso,
            "fase": fase,
            "es_noche": fase == "noche",
            "factor_luz": max(0.05, min(1.0, factor_luz)),
        }
        return self.estado_tiempo
        
    def simular_turno_ia(self):
        """Ejecuta un 'tick' de IA: comer, morir y reproducirse."""
        # "Este es el método más complejo. Es el 'Turno' de IA
        # que 'main' llama cada 'TURNO_DURACION_MS'."
        estado_tiempo = self._actualizar_estado_tiempo(avanzar=True)
        self.eventos_visuales.clear() # "Limpia la cola de eventos del turno anterior."
        
        peces_muertos, truchas_muertas, tiburones_muertos = [], [], []
        plantas_comidas = []
        nuevas_crias_peces, nuevas_crias_truchas, nuevas_crias_tiburones = [], [], []

        # "Pasamos un diccionario de las listas a cada animal.
        # Esto es una forma de 'Inyección de Dependencias' simple."
        listas_de_seres = {
            "peces": self.peces,
            "truchas": self.truchas,
            "tiburones": self.tiburones,
            "plantas": self.plantas,
            "estado_tiempo": estado_tiempo,
        }

        # "Bucle de Peces: Decidir, Comer, Reproducirse, Morir."
        for pez in self.peces:
            pez.update_decision_turno(listas_de_seres) 
            for planta in self.plantas:
                # "Usamos 'colliderect' para la interacción."
                if pez.rect.colliderect(planta.rect) and planta not in plantas_comidas:
                    energia_ganada = pez.comer(planta)
                    if energia_ganada > 0:
                        # "¡COMUNICACIÓN! Añadimos un evento para la Vista."
                        self.eventos_visuales.append(('comer_pez', pez.rect.center, energia_ganada))
                    plantas_comidas.append(planta)
                    break # "El pez solo come una planta por turno."
            cria = pez.reproducir(estado_tiempo)
            if cria and (len(self.peces) + len(nuevas_crias_peces) < POBLACION_LIMITES["peces"]["max"]):
                nuevas_crias_peces.append(cria) 
                self.eventos_visuales.append(('aparearse', pez.rect.center, 'pez'))
                self.eventos_visuales.append(('nacer', cria.rect.center, 'pez'))
            if pez.ha_muerto():
                peces_muertos.append(pez)
                self.eventos_visuales.append(('morir', pez.rect.center))

        # "Bucle de Truchas: Decidir (con fuga), Cazar Peces, Reproducirse, Morir."
        for trucha in self.truchas:
            trucha.update_decision_turno(listas_de_seres)
            for pez in self.peces:
                if pez not in peces_muertos and trucha.rect.colliderect(pez.rect):
                    energia_ganada = trucha.comer(pez)
                    if energia_ganada > 0:
                        self.eventos_visuales.append(('comer_depredador', trucha.rect.center, energia_ganada))
                    if pez not in peces_muertos:
                        peces_muertos.append(pez) # "Marca al pez para eliminarlo."
                        self.eventos_visuales.append(('morir', pez.rect.center))
                    break
            cria = trucha.reproducir(estado_tiempo)
            if cria and (len(self.truchas) + len(nuevas_crias_truchas) < POBLACION_LIMITES["truchas"]["max"]):
                nuevas_crias_truchas.append(cria)
                self.eventos_visuales.append(('aparearse', trucha.rect.center, 'trucha'))
                self.eventos_visuales.append(('nacer', cria.rect.center, 'trucha'))
            if trucha.ha_muerto():
                truchas_muertas.append(trucha)
                self.eventos_visuales.append(('morir', trucha.rect.center))

        # "Bucle de Tiburones: Decidir, Cazar Truchas, Reproducirse, Morir."
        for tiburon in self.tiburones:
            tiburon.update_decision_turno(listas_de_seres)
            consumio_presa = False
            for trucha in self.truchas:
                if trucha not in truchas_muertas and tiburon.rect.colliderect(trucha.rect):
                    energia_ganada = tiburon.comer(trucha)
                    if energia_ganada > 0:
                        self.eventos_visuales.append(('comer_depredador', tiburon.rect.center, energia_ganada))
                    if trucha not in truchas_muertas:
                        truchas_muertas.append(trucha)
                        self.eventos_visuales.append(('morir', trucha.rect.center))
                    consumio_presa = True
                    break
            if not consumio_presa:
                for pez in self.peces:
                    if pez not in peces_muertos and tiburon.rect.colliderect(pez.rect):
                        energia_ganada = tiburon.comer(pez)
                        if energia_ganada > 0:
                            self.eventos_visuales.append(('comer_depredador', tiburon.rect.center, energia_ganada))
                        if pez not in peces_muertos:
                            peces_muertos.append(pez)
                            self.eventos_visuales.append(('morir', pez.rect.center))
                        break
            cria = tiburon.reproducir(estado_tiempo)
            if cria and (len(self.tiburones) + len(nuevas_crias_tiburones) < POBLACION_LIMITES["tiburones"]["max"]):
                nuevas_crias_tiburones.append(cria)
                self.eventos_visuales.append(('aparearse', tiburon.rect.center, 'tiburon'))
                self.eventos_visuales.append(('nacer', cria.rect.center, 'tiburon'))
            if tiburon.ha_muerto():
                tiburones_muertos.append(tiburon)
                self.eventos_visuales.append(('morir', tiburon.rect.center))

        # "Fase de 'Limpieza' del turno."
        # "No modificamos las listas mientras iteramos. Usamos 'sets'
        # para una eliminación eficiente (O(1) en lugar de O(N))."
        set_peces_muertos = set(peces_muertos)
        set_truchas_muertas = set(truchas_muertas)
        set_tiburones_muertos = set(tiburones_muertos)
        set_plantas_comidas = set(plantas_comidas)

        # "Reconstruimos las listas usando 'list comprehension'.
        # Es más limpio y eficiente que 'list.remove()'."
        self.peces = [p for p in self.peces if p not in set_peces_muertos]
        self.truchas = [t for t in self.truchas if t not in set_truchas_muertas]
        self.tiburones = [t for t in self.tiburones if t not in set_tiburones_muertos]
        self.plantas = [p for p in self.plantas if p not in set_plantas_comidas]

        # "Fase de 'Nacimiento'. Añadimos las crías al final."
        self.peces.extend(nuevas_crias_peces)
        self.truchas.extend(nuevas_crias_truchas)
        self.tiburones.extend(nuevas_crias_tiburones)
        self._balancear_poblaciones()

        fase_actual = estado_tiempo.get("fase") if estado_tiempo else "dia"
        if fase_actual in ("amanecer", "dia"):
            prob_regeneracion = 0.9
        elif fase_actual == "atardecer":
            prob_regeneracion = 0.6
        else:
            prob_regeneracion = 0.35
        if (len(self.plantas) < POBLACION_LIMITES["plantas"]["max"] and
                random.random() < prob_regeneracion):
            # "Regeneración de recursos dependiente de la luz solar."
            self.plantas.append(Planta("Alga", 20))
            
    def get_all_entities(self):
        """Devuelve todas las listas de entidades para la Vista."""
        # "Este es el 'API' que la Vista usa para LEER el estado."
        return self.plantas, self.peces, self.truchas, self.tiburones

    def get_estado_tiempo(self):
        """Expone una copia del estado del ciclo día/noche para la Vista."""
        return dict(self.estado_tiempo)

    def actualizar_movimiento_frame(self):
        """Actualiza el movimiento continuo de todas las criaturas."""
        # "Este es el 'API' que 'main' llama 60 veces por segundo."
        todos_los_animales = self.peces + self.truchas + self.tiburones
        for animal in todos_los_animales:
            animal.update_movimiento_frame()

    def _balancear_poblaciones(self):
        """Garantiza que cada especie se mantenga dentro de los límites configurados."""
        self._ajustar_especie(
            'plantas',
            lambda: Planta("Alga", 20),
            POBLACION_LIMITES["plantas"]["min"],
            POBLACION_LIMITES["plantas"]["max"],
            icono=None,
        )
        self._ajustar_especie(
            'peces',
            lambda: Pez("Pejerrey", 70, 120),
            POBLACION_LIMITES["peces"]["min"],
            POBLACION_LIMITES["peces"]["max"],
            icono='pez',
        )
        self._ajustar_especie(
            'truchas',
            lambda: Trucha("Trucha", 120, 180),
            POBLACION_LIMITES["truchas"]["min"],
            POBLACION_LIMITES["truchas"]["max"],
            icono='trucha',
        )
        self._ajustar_especie(
            'tiburones',
            lambda: Tiburon("Tiburon", 200, 30),
            POBLACION_LIMITES["tiburones"]["min"],
            POBLACION_LIMITES["tiburones"]["max"],
            icono='tiburon',
        )

    def _ajustar_especie(self, atributo, factory, minimo, maximo, icono=None):
        """Recorta o refuerza una lista concreta según limites min/max."""
        lista = getattr(self, atributo)
        exceso = len(lista) - maximo
        if exceso > 0:
            random.shuffle(lista)
            for _ in range(exceso):
                lista.pop()
        deficit = minimo - len(lista)
        if deficit > 0:
            for _ in range(deficit):
                nuevo = factory()
                lista.append(nuevo)
                if icono:
                    self.eventos_visuales.append(('nacer', nuevo.rect.center, icono))
