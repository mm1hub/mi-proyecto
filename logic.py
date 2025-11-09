import pygame
import random
from abc import ABC, abstractmethod

# ---------------------------------
# CONFIGURACIÃ“N GLOBAL (compartida)
# ---------------------------------
WIDTH, HEIGHT = 1024, 768
FPS = 30
TURNO_DURACION_MS = 1000  # Un turno de IA cada 1 s para ciclos mÃ¡s largos

# Colores (usados por la Vista, pero importados desde aquÃ­)
BLANCO = (255, 255, 255)
AZUL = (0, 0, 255)
VERDE = (0, 255, 0)
MARRON = (139, 69, 19)
GRIS = (169, 169, 169)

# Configuración de texturas: edita aquí los nombres de archivo y tamaños
# Puedes usar un string (un único nombre) o una lista de nombres alternativos por entidad.
TEXTURAS = {
    'pez': ['pez.png', 'pez.gif', 'fish.png'],
    'trucha': ['trucha.png', 'trucha.gif'],
    'tiburon': ['tiburon.png', 'tiburon.gif', 'shark.png'],
    'alga': ['algagif.gif', 'alga.png', 'alga.gif'],
}

# Tamaños visuales de cada entidad (ancho, alto)
TEXTURAS_TAM = {
    'pez': (20, 20),
    'trucha': (35, 35),
    'tiburon': (45, 45),
    'alga': (14, 14),
}

# --- Colores para la VISTA (UI y Fondo) ---
AGUA_CLARA = (173, 216, 230)
AGUA_OSCURA = (0, 105, 148)
NEGRO_UI = (20, 20, 20) # Para textos de UI

# --- NUEVOS COLORES PARA BOTONES ---
COLOR_TEXTO_BTN = (255, 255, 255)
COLOR_START = (40, 167, 69)
COLOR_STOP = (220, 53, 69)
COLOR_PAUSE = (255, 193, 7)
COLOR_RESUME = (23, 162, 184)


# ---------------------------------
# CAPA DE LÃ“GICA (MODELO)
# (El resto de este archivo es EXACTAMENTE el que tÃº enviaste)
# ---------------------------------

class Animal(ABC):
    def __init__(self, nombre, energia, tiempo_vida, ancho=10, alto=10):
        self.nombre = nombre
        self.energia = energia
        self.tiempo_vida = tiempo_vida
        self.edad = 0
        self.rect = pygame.Rect(
            random.randint(0, max(0, WIDTH - ancho)),
            random.randint(0, max(0, HEIGHT - alto)),
            ancho,
            alto,
        )
        self.target_x = float(self.rect.x)
        self.target_y = float(self.rect.y)
        self.velocidad_frame = random.uniform(1.0, 3.0)
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        if self.rect.right > WIDTH: self.rect.right = WIDTH
        if self.rect.bottom > HEIGHT: self.rect.bottom = HEIGHT
        self.pos_x, self.pos_y = float(self.rect.x), float(self.rect.y)
        self.target_x, self.target_y = self.pos_x, self.pos_y

    @abstractmethod
    def decidir_objetivo(self, listas_de_seres):
        pass
    @abstractmethod
    def comer(self, objetivo):
        pass
    @abstractmethod
    def reproducir(self):
        pass

    def update_decision_turno(self, listas_de_seres):
        self.energia -= 2
        self.edad += 1
        self.decidir_objetivo(listas_de_seres)

    def update_movimiento_frame(self):
        dx = self.target_x - self.pos_x
        dy = self.target_y - self.pos_y
        if abs(dx) > 0:
            step_x = max(-self.velocidad_frame, min(self.velocidad_frame, dx))
            self.pos_x += step_x
        if abs(dy) > 0:
            step_y = max(-self.velocidad_frame, min(self.velocidad_frame, dy))
            self.pos_y += step_y
        max_x = max(0, WIDTH - self.rect.width)
        max_y = max(0, HEIGHT - self.rect.height)
        self.pos_x = max(0.0, min(self.pos_x, float(max_x)))
        self.pos_y = max(0.0, min(self.pos_y, float(max_y)))
        self.rect.topleft = (int(self.pos_x), int(self.pos_y))

    def ha_muerto(self):
        return self.edad >= self.tiempo_vida or self.energia <= 0

class Planta:
    def __init__(self, nombre, energia):
        self.nombre = nombre
        self.energia = energia
        self.rect = pygame.Rect(
            random.randint(0, max(0, WIDTH - 14)),
            random.randint(0, max(0, HEIGHT - 14)),
            14,
            14,
        )

class Pez(Animal):
    def __init__(self, nombre, energia, tiempo_vida):
        super().__init__(nombre, energia, tiempo_vida, ancho=20, alto=20)
        self.velocidad_frame = random.uniform(2.0, 4.0)

    def comer(self, planta):
        if isinstance(planta, Planta):
            self.energia += planta.energia

    def reproducir(self):
        if self.energia > 100 and self.edad > 5 and random.random() < 0.1:
            self.energia -= 50
            cria = Pez("Pejerrey", 50, 20)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

    def decidir_objetivo(self, listas_de_seres):
        lista_depredadores = listas_de_seres["truchas"] + listas_de_seres["tiburones"]
        lista_de_plantas = listas_de_seres["plantas"]
        rango_vision_depredador = 150 * 150
        rango_vision_planta = 100 * 100
        depredador_cercano = None
        planta_cercana = None
        dist_min_depredador = rango_vision_depredador
        dist_min_planta = rango_vision_planta

        for dep in lista_depredadores:
            distancia = (self.rect.centerx - dep.rect.centerx) ** 2 + (self.rect.centery - dep.rect.centery) ** 2
            if distancia < dist_min_depredador:
                dist_min_depredador = distancia
                depredador_cercano = dep

        if self.energia < 70:
            for planta in lista_de_plantas:
                distancia = (self.rect.centerx - planta.rect.centerx) ** 2 + (self.rect.centery - planta.rect.centery) ** 2
                if distancia < dist_min_planta:
                    dist_min_planta = distancia
                    planta_cercana = planta
        
        if depredador_cercano:
            if self.rect.centerx < depredador_cercano.rect.centerx: self.target_x = self.rect.x - 70
            else: self.target_x = self.rect.x + 70
            if self.rect.centery < depredador_cercano.rect.centery: self.target_y = self.rect.y - 70
            else: self.target_y = self.rect.y + 70
        elif self.energia < 70 and planta_cercana:
            self.target_x = float(planta_cercana.rect.centerx)
            self.target_y = float(planta_cercana.rect.centery)
        else:
            if abs(self.rect.x - self.target_x) < 5 and abs(self.rect.y - self.target_y) < 5:
                self.target_x = self.rect.x + random.randint(-70, 70)
                self.target_y = self.rect.y + random.randint(-70, 70)

        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Carnivoro(Animal):
    def __init__(self, nombre, energia, tiempo_vida, presa_key, hambre_threshold, ancho=12, alto=12):
        super().__init__(nombre, energia, tiempo_vida, ancho=ancho, alto=alto)
        self.presa_key = presa_key
        self.hambre_threshold = hambre_threshold

    def decidir_objetivo(self, listas_de_seres):
        lista_de_presas = listas_de_seres[self.presa_key]
        presa_cercana = None
        distancia_minima = float('inf')

        if self.energia < self.hambre_threshold:
            for presa in lista_de_presas:
                distancia = (self.rect.centerx - presa.rect.centerx) ** 2 + (self.rect.centery - presa.rect.centery) ** 2
                if distancia < distancia_minima:
                    distancia_minima = distancia
                    presa_cercana = presa

        if presa_cercana:
            self.target_x = float(presa_cercana.rect.centerx)
            self.target_y = float(presa_cercana.rect.centery)
        else:
            if abs(self.rect.x - self.target_x) < 5 and abs(self.rect.y - self.target_y) < 5:
                self.target_x = self.rect.x + random.randint(-50, 50)
                self.target_y = self.rect.y + random.randint(-50, 50)

        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

class Trucha(Carnivoro):
    def __init__(self, nombre, energia, tiempo_vida):
        super().__init__(nombre, energia, tiempo_vida, presa_key="peces", hambre_threshold=80, ancho=35, alto=35)
        self.velocidad_frame = random.uniform(1.5, 3.5)

    def comer(self, pez):
        if isinstance(pez, Pez):
            self.energia += pez.energia // 2

    def reproducir(self):
        if self.energia > 150 and self.edad > 8 and random.random() < 0.05:
            self.energia -= 70
            cria = Trucha("Trucha", 100, 25)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Tiburon(Carnivoro):
    def __init__(self, nombre, energia, tiempo_vida):
        super().__init__(nombre, energia, tiempo_vida, presa_key="truchas", hambre_threshold=150, ancho=45, alto=45)
        self.velocidad_frame = random.uniform(1.0, 3.0)

    def comer(self, trucha):
        if isinstance(trucha, Trucha):
            self.energia += trucha.energia // 2

    def reproducir(self):
        if self.energia > 200 and self.edad > 10 and random.random() < 0.03:
            self.energia -= 100
            cria = Tiburon("TiburÃ³n", 200, 30)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Ecosistema:
    def __init__(self):
        self.peces = []
        self.truchas = []
        self.tiburones = []
        self.plantas = []

    def poblar_inicial(self):
        self.poblar_custom()

    def poblar_custom(self, n_plantas=25, n_peces=15, n_truchas=5, n_tiburones=2):
        self.plantas = [Planta("Alga", 20) for _ in range(n_plantas)]
        self.peces = [Pez("Pejerrey", 70, 120) for _ in range(n_peces)]
        self.truchas = [Trucha("Trucha", 120, 180) for _ in range(n_truchas)]
        self.tiburones = [Tiburon("Tiburon", 200, 30) for _ in range(n_tiburones)]
    def simular_turno_ia(self):
        peces_muertos, truchas_muertas, tiburones_muertos = [], [], []
        plantas_comidas = []
        nuevas_crias_peces, nuevas_crias_truchas, nuevas_crias_tiburones = [], [], []

        listas_de_seres = {
            "peces": self.peces,
            "truchas": self.truchas,
            "tiburones": self.tiburones,
            "plantas": self.plantas
        }

        for pez in self.peces:
            pez.update_decision_turno(listas_de_seres)
            for planta in self.plantas:
                if pez.rect.colliderect(planta.rect) and planta not in plantas_comidas:
                    pez.comer(planta)
                    plantas_comidas.append(planta)
                    break
            cria = pez.reproducir()
            if cria:
                nuevas_crias_peces.append(cria)
            if pez.ha_muerto():
                peces_muertos.append(pez)

        for trucha in self.truchas:
            trucha.update_decision_turno(listas_de_seres)
            for pez in self.peces:
                if pez not in peces_muertos and trucha.rect.colliderect(pez.rect):
                    trucha.comer(pez)
                    if pez not in peces_muertos:
                        peces_muertos.append(pez)
                    break
            cria = trucha.reproducir()
            if cria:
                nuevas_crias_truchas.append(cria)
            if trucha.ha_muerto():
                truchas_muertas.append(trucha)

        for tiburon in self.tiburones:
            tiburon.update_decision_turno(listas_de_seres)
            for trucha in self.truchas:
                if trucha not in truchas_muertas and tiburon.rect.colliderect(trucha.rect):
                    tiburon.comer(trucha)
                    if trucha not in truchas_muertas:
                        truchas_muertas.append(trucha)
                    break
            cria = tiburon.reproducir()
            if cria:
                nuevas_crias_tiburones.append(cria)
            if tiburon.ha_muerto():
                tiburones_muertos.append(tiburon)

        set_peces_muertos = set(peces_muertos)
        set_truchas_muertas = set(truchas_muertas)
        set_tiburones_muertos = set(tiburones_muertos)
        set_plantas_comidas = set(plantas_comidas)

        self.peces = [p for p in self.peces if p not in set_peces_muertos]
        self.truchas = [t for t in self.truchas if t not in set_truchas_muertas]
        self.tiburones = [t for t in self.tiburones if t not in set_tiburones_muertos]
        self.plantas = [p for p in self.plantas if p not in set_plantas_comidas]

        self.peces.extend(nuevas_crias_peces)
        self.truchas.extend(nuevas_crias_truchas)
        self.tiburones.extend(nuevas_crias_tiburones)

        if random.random() < 0.8:
            self.plantas.append(Planta("Alga", 20))

    def actualizar_movimiento_frame(self):
        todos_los_animales = self.peces + self.truchas + self.tiburones
        for animal in todos_los_animales:
            animal.update_movimiento_frame()




