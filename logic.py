import pygame
import random
from abc import ABC, abstractmethod

# ---------------------------------
# CONFIGURACIÓN GLOBAL (compartida)
# ---------------------------------
# Aumentamos el tamaño por defecto para que la interfaz tenga más espacio
# Mantener altura para pantallas 768p y ampliar ancho para evitar solapamientos
WIDTH, HEIGHT = 1280, 768
FPS = 30
TURNO_DURACION_MS = 1000  # Un turno de IA cada 1 s para ciclos mas largos
# Tamano de celda para particion espacial (mejora de rendimiento)
GRID_CELDA = 64

# Colores (usados por la Vista, pero importados desde aquí)
BLANCO = (255, 255, 255)
AZUL = (0, 0, 255)
VERDE = (0, 255, 0)
MARRON = (139, 69, 19)
GRIS = (169, 169, 169)

# Configuración de texturas: edita aquí los nombres de archivo y tamaños
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

# --- (IDEA 3) Colores para Partículas de Eventos ---
COLOR_COMER = (144, 238, 144) # Verde claro
COLOR_NACER = (255, 182, 193) # Rosa claro
COLOR_MORIR = (160, 160, 160) # Gris

# --- (IDEA 10) Color para Burbujas ---
COLOR_BURBUJA = (200, 225, 255)


# ---------------------------------
# CAPA DE LÓGICA (MODELO)
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
        # Velocidad actual (vector) para movimiento más suave
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.pos_x = float(self.rect.x)
        self.pos_y = float(self.rect.y)
        
        # --- (IDEA 2) Añadir rastreador de dirección ---
        self.direccion_h = 1 # 1 = derecha, -1 = izquierda
        # Saciedad para alimentacion adaptativa (en turnos)
        self.saciedad = 0
        # Entorno favorable para reproducirse (determinado en decidir_objetivo)
        self.entorno_favorable_repro = False
        
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
        # Gasto energetico por turno con pequeno ajuste por envejecimiento
        coste = 2
        if self.edad > int(self.tiempo_vida * 0.7):
            coste += 1
        self.energia -= coste
        self.edad += 1
        if self.saciedad > 0:
            self.saciedad -= 1
        self.decidir_objetivo(listas_de_seres)

    def steering_extra(self, vecinos):
        """Gancho para que subclases aporten steering adicional.
        Devuelve una tupla (dx, dy) en unidades de velocidad deseada.
        Por defecto no aplica cambios.
        """
        return 0.0, 0.0

    def update_movimiento_frame(self, vecinos=None):
        # Steering basico hacia el objetivo con llegada suave y jitter
        dx = self.target_x - self.pos_x
        dy = self.target_y - self.pos_y

        dist_sq = dx*dx + dy*dy
        dist = dist_sq ** 0.5 if dist_sq > 0 else 0.0

        max_speed = float(self.velocidad_frame)
        # Reducir fuerza para giros más suaves
        max_force = 0.22  # aceleración máxima por frame

        desired_x, desired_y = 0.0, 0.0
        if dist > 0.001:
            # Llegada suave: reduce velocidad al acercarse
            slow_radius = 80.0
            desired_speed = max_speed if dist > slow_radius else max(0.4, max_speed * (dist / slow_radius))
            inv_d = desired_speed / dist
            desired_x = dx * inv_d
            desired_y = dy * inv_d

        # Separación simple para evitar que se peguen
        sep_x, sep_y = 0.0, 0.0
        if vecinos:
            sep_radius = 28.0
            # Pesar separación para que no domine el objetivo
            sep_weight = 0.6
            total = 0
            for other in vecinos:
                if other is self:
                    continue
                ox = (other.rect.x + other.rect.width * 0.5)
                oy = (other.rect.y + other.rect.height * 0.5)
                sx = self.pos_x + self.rect.width * 0.5
                sy = self.pos_y + self.rect.height * 0.5
                ddx = sx - ox
                ddy = sy - oy
                d2 = ddx*ddx + ddy*ddy
                if d2 > 0 and d2 < sep_radius * sep_radius:
                    d = d2 ** 0.5
                    if d > 0:
                        # Más fuerza cuanto más cerca
                        repel = (sep_radius - d) / sep_radius
                        sep_x += (ddx / d) * repel
                        sep_y += (ddy / d) * repel
                        total += 1
            if total > 0:
                sep_x /= total
                sep_y /= total
                # Limitar magnitud de la separación
                m2 = sep_x*sep_x + sep_y*sep_y
                if m2 > 1.0:
                    m = m2 ** 0.5
                    sep_x /= m
                    sep_y /= m
                sep_x *= sep_weight
                sep_y *= sep_weight
        # Paredes: empuje suave hacia adentro si está muy cerca del borde
        margin = 20.0
        if self.pos_x < margin:
            sep_x += (margin - self.pos_x) / margin
        elif self.pos_x > WIDTH - self.rect.width - margin:
            sep_x -= (self.pos_x - (WIDTH - self.rect.width - margin)) / margin
        if self.pos_y < margin:
            sep_y += (margin - self.pos_y) / margin
        elif self.pos_y > HEIGHT - self.rect.height - margin:
            sep_y -= (self.pos_y - (HEIGHT - self.rect.height - margin)) / margin

        # Combinar deseos: objetivo + separacion
        desired_x += sep_x * max_speed
        desired_y += sep_y * max_speed

        # Ajuste especifico de especie (p.ej. cardumen)
        try:
            extra_x, extra_y = self.steering_extra(vecinos or [])
            desired_x += extra_x
            desired_y += extra_y
        except Exception:
            pass

        # Calcular steering
        steer_x = desired_x - self.vel_x
        steer_y = desired_y - self.vel_y
        # Limitar fuerza
        mag_steer_sq = steer_x*steer_x + steer_y*steer_y
        if mag_steer_sq > max_force*max_force:
            mag_steer = mag_steer_sq ** 0.5
            if mag_steer > 0:
                scale = max_force / mag_steer
                steer_x *= scale
                steer_y *= scale

        # Pequeño jitter para hacerlo más orgánico (reducido)
        jitter = 0.02
        steer_x += random.uniform(-jitter, jitter)
        steer_y += random.uniform(-jitter, jitter)

        # Aplicar aceleración
        self.vel_x += steer_x
        self.vel_y += steer_y

        # Suavizar con amortiguación ligera para evitar oscilaciones
        damping = 0.98
        self.vel_x *= damping
        self.vel_y *= damping

        # Limitar velocidad
        vel_sq = self.vel_x*self.vel_x + self.vel_y*self.vel_y
        if vel_sq > max_speed*max_speed:
            v = vel_sq ** 0.5
            if v > 0:
                s = max_speed / v
                self.vel_x *= s
                self.vel_y *= s

        # Actualizar posición
        self.pos_x += self.vel_x
        self.pos_y += self.vel_y

        # Si estamos muy cerca del objetivo, amortiguar velocidad para evitar órbitas
        if dist < 1.2:
            self.vel_x *= 0.5
            self.vel_y *= 0.5

        # Dirección horizontal para sprites
        if abs(self.vel_x) > 0.01:
            self.direccion_h = 1 if self.vel_x > 0 else -1

        # Confinar a la pantalla y amortiguar si toca bordes
        max_x = max(0, WIDTH - self.rect.width)
        max_y = max(0, HEIGHT - self.rect.height)
        out_x = False
        out_y = False
        if self.pos_x < 0.0:
            self.pos_x = 0.0
            out_x = True
        elif self.pos_x > float(max_x):
            self.pos_x = float(max_x)
            out_x = True
        if self.pos_y < 0.0:
            self.pos_y = 0.0
            out_y = True
        elif self.pos_y > float(max_y):
            self.pos_y = float(max_y)
            out_y = True
        if out_x:
            self.vel_x *= -0.5
        if out_y:
            self.vel_y *= -0.5

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
            self.saciedad = max(self.saciedad, 2)
            return planta.energia # Devuelve cuánta energía ganó
        return 0

    def reproducir(self):
        if self.energia > 100 and self.edad > 5 and self.entorno_favorable_repro and random.random() < 0.1:
            self.energia -= 50
            cria = Pez("Pejerrey", 50, 20)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

    def steering_extra(self, vecinos):
        # Comportamiento de cardumen (cohesion + alineacion)
        if not vecinos:
            return 0.0, 0.0
        rango = 85.0
        rango2 = rango * rango
        sum_x, sum_y = 0.0, 0.0  # centro de masas
        avg_vx, avg_vy = 0.0, 0.0  # alineacion con velocidades
        conteo = 0
        cx = self.pos_x + self.rect.width * 0.5
        cy = self.pos_y + self.rect.height * 0.5
        for o in vecinos:
            if o is self or not isinstance(o, Pez):
                continue
            ox = o.pos_x + o.rect.width * 0.5
            oy = o.pos_y + o.rect.height * 0.5
            dx = ox - cx
            dy = oy - cy
            d2 = dx*dx + dy*dy
            if d2 <= rango2 and d2 > 1e-6:
                sum_x += ox
                sum_y += oy
                avg_vx += o.vel_x
                avg_vy += o.vel_y
                conteo += 1
        if conteo == 0:
            return 0.0, 0.0
        # Cohesion: hacia el centro del grupo
        cm_x = sum_x / conteo
        cm_y = sum_y / conteo
        coh_x = cm_x - cx
        coh_y = cm_y - cy
        # Normalizar cohesion a una magnitud maxima
        mag2 = coh_x*coh_x + coh_y*coh_y
        if mag2 > 0:
            mag = mag2 ** 0.5
            coh_x /= mag
            coh_y /= mag
        # Alineacion: hacia la velocidad promedio del grupo
        ali_x = avg_vx / conteo
        ali_y = avg_vy / conteo
        # Limitar alineacion
        ali_mag2 = ali_x*ali_x + ali_y*ali_y
        if ali_mag2 > 1.0:
            ali_mag = ali_mag2 ** 0.5
            ali_x /= ali_mag
            ali_y /= ali_mag
        # Pesos suaves para no dominar al objetivo principal
        w_coh = 0.35 * self.velocidad_frame
        w_ali = 0.50 * self.velocidad_frame
        return coh_x * w_coh + ali_x * w_ali, coh_y * w_coh + ali_y * w_ali

    def decidir_objetivo(self, listas_de_seres):
        lista_depredadores = listas_de_seres["truchas"] + listas_de_seres["tiburones"]
        lista_de_plantas = listas_de_seres["plantas"]
        rango_dep2 = 170 * 170
        rango_pl2 = 110 * 110
        depredador_cercano = None
        planta_cercana = None
        dist_min_dep = rango_dep2
        dist_min_pl = rango_pl2

        cx, cy = self.rect.centerx, self.rect.centery
        for dep in lista_depredadores:
            dx = cx - dep.rect.centerx
            dy = cy - dep.rect.centery
            d2 = dx*dx + dy*dy
            if d2 < dist_min_dep:
                dist_min_dep = d2
                depredador_cercano = dep

        necesita_comer = (self.saciedad == 0) and (self.energia < 70 or self.energia < 0.8 * getattr(self, 'energia_max', 120))
        if necesita_comer:
            for planta in lista_de_plantas:
                dx = cx - planta.rect.centerx
                dy = cy - planta.rect.centery
                d2 = dx*dx + dy*dy
                if d2 < dist_min_pl:
                    dist_min_pl = d2
                    planta_cercana = planta
        
        if depredador_cercano is not None:
            # Evadir alejandose del depredador mas cercano con un poco de ruido
            vx = cx - depredador_cercano.rect.centerx
            vy = cy - depredador_cercano.rect.centery
            mag2 = vx*vx + vy*vy
            if mag2 > 0:
                mag = mag2 ** 0.5
                vx /= mag
                vy /= mag
            distancia_evade = 120.0
            perp = (-vy, vx)
            jitter = random.uniform(-25.0, 25.0)
            tx = cx + vx * distancia_evade + perp[0] * (jitter * 0.1)
            ty = cy + vy * distancia_evade + perp[1] * (jitter * 0.1)
            self.target_x = max(0, min(tx - self.rect.width * 0.5, WIDTH - self.rect.width))
            self.target_y = max(0, min(ty - self.rect.height * 0.5, HEIGHT - self.rect.height))
        elif necesita_comer and planta_cercana is not None:
            self.target_x = float(planta_cercana.rect.centerx)
            self.target_y = float(planta_cercana.rect.centery)
        else:
            if abs(self.rect.x - self.target_x) < 5 and abs(self.rect.y - self.target_y) < 5:
                self.target_x = self.rect.x + random.randint(-70, 70)
                self.target_y = self.rect.y + random.randint(-70, 70)

        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

        # Entorno de reproduccion: plantas disponibles y sin depredador inmediato
        plantas_cercanas = 0
        for planta in lista_de_plantas:
            dx = cx - planta.rect.centerx
            dy = cy - planta.rect.centery
            if dx*dx + dy*dy <= (140*140):
                plantas_cercanas += 1
                if plantas_cercanas >= 2:
                    break
        self.entorno_favorable_repro = (plantas_cercanas >= 2) and (depredador_cercano is None)

class Carnivoro(Animal):
    def __init__(self, nombre, energia, tiempo_vida, presa_key, hambre_threshold, ancho=12, alto=12):
        super().__init__(nombre, energia, tiempo_vida, ancho=ancho, alto=alto)
        self.presa_key = presa_key
        self.hambre_threshold = hambre_threshold
        # Rango de busqueda y comportamiento de oportunidad
        self.sensor_rango = 240.0
        self.oportunidad_prob = 0.35
        self.energia_max = 300

    def decidir_objetivo(self, listas_de_seres):
        lista_de_presas = listas_de_seres[self.presa_key]
        presa_cercana = None
        distancia_minima2 = float('inf')
        cx, cy = self.rect.centerx, self.rect.centery
        sensor2 = self.sensor_rango * self.sensor_rango

        # Ajuste de umbral por edad y saciedad
        umbral = self.hambre_threshold
        if self.edad > int(self.tiempo_vida * 0.7):
            umbral = int(umbral * 1.1)
        perseguir = (self.saciedad == 0) and (self.energia < umbral)
        if not perseguir and random.random() < self.oportunidad_prob:
            perseguir = True

        # Riesgo (trucha evita tiburon cercano si no esta muy hambrienta)
        riesgo_alto = False
        if isinstance(self, Trucha):
            for tb in listas_de_seres.get("tiburones", []):
                dx = cx - tb.rect.centerx
                dy = cy - tb.rect.centery
                if dx*dx + dy*dy <= (180*180):
                    riesgo_alto = True
                    break

        if perseguir:
            for presa in lista_de_presas:
                dx = cx - presa.rect.centerx
                dy = cy - presa.rect.centery
                d2 = dx*dx + dy*dy
                if d2 < sensor2 and d2 < distancia_minima2:
                    distancia_minima2 = d2
                    presa_cercana = presa

        if presa_cercana is not None and not (riesgo_alto and self.energia > umbral * 0.8):
            # Prediccion simple: apuntar donde estara la presa
            dist = distancia_minima2 ** 0.5 if distancia_minima2 < float('inf') else 0.0
            lead = min(1.2, dist / max(1.0, self.velocidad_frame * 12.0))
            pred_x = presa_cercana.rect.centerx + presa_cercana.vel_x * lead * 12.0
            pred_y = presa_cercana.rect.centery + presa_cercana.vel_y * lead * 12.0
            self.target_x = float(pred_x)
            self.target_y = float(pred_y)
        else:
            # Patrullar
            if abs(self.rect.x - self.target_x) < 5 and abs(self.rect.y - self.target_y) < 5:
                self.target_x = self.rect.x + random.randint(-50, 50)
                self.target_y = self.rect.y + random.randint(-50, 50)

        self.target_x = max(0, min(self.target_x, WIDTH - self.rect.width))
        self.target_y = max(0, min(self.target_y, HEIGHT - self.rect.height))

        # Entorno para reproduccion (presas cercanas y, en trucha, bajo riesgo)
        presas_cercanas = 0
        for pr in lista_de_presas:
            dx = cx - pr.rect.centerx
            dy = cy - pr.rect.centery
            if dx*dx + dy*dy <= (180*180):
                presas_cercanas += 1
                if presas_cercanas >= 2:
                    break
        self.entorno_favorable_repro = (presas_cercanas >= 2) and (not (isinstance(self, Trucha) and riesgo_alto))

class Trucha(Carnivoro):
    def __init__(self, nombre, energia, tiempo_vida):
        super().__init__(nombre, energia, tiempo_vida, presa_key="peces", hambre_threshold=80, ancho=35, alto=35)
        self.velocidad_frame = random.uniform(1.5, 3.5)

    def comer(self, pez):
        if isinstance(pez, Pez):
            energia_ganada = pez.energia // 2
            self.energia += energia_ganada
            self.saciedad = max(self.saciedad, 2)
            return energia_ganada
        return 0

    def reproducir(self):
        if self.energia > 150 and self.edad > 8 and self.entorno_favorable_repro and random.random() < 0.05:
            self.energia -= 70
            cria = Trucha("Trucha", 100, 25)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Tiburon(Carnivoro):
    def __init__(self, nombre, energia, tiempo_vida):
        super().__init__(nombre, energia, tiempo_vida, presa_key="truchas", hambre_threshold=150, ancho=45, alto=45)
        self.velocidad_frame = random.uniform(1.0, 3.0)
        self.sensor_rango = 280.0

    def comer(self, trucha):
        if isinstance(trucha, Trucha):
            energia_ganada = trucha.energia // 2
            self.energia += energia_ganada
            self.saciedad = max(self.saciedad, 2)
            return energia_ganada
        return 0

    def reproducir(self):
        if self.energia > 200 and self.edad > 10 and self.entorno_favorable_repro and random.random() < 0.03:
            self.energia -= 100
            cria = Tiburon("Tiburón", 200, 30)
            cria.rect.topleft = self.rect.topleft
            return cria
        return None

class Ecosistema:
    def __init__(self):
        self.peces = []
        self.truchas = []
        self.tiburones = []
        self.plantas = []
        # --- (IDEA 3/9) Lista para que la Vista lea los eventos ---
        self.eventos_visuales = []

    def poblar_inicial(self):
        self.poblar_custom()

    def poblar_custom(self, n_plantas=25, n_peces=15, n_truchas=5, n_tiburones=2):
        self.plantas = [Planta("Alga", 20) for _ in range(n_plantas)]
        self.peces = [Pez("Pejerrey", 70, 120) for _ in range(n_peces)]
        self.truchas = [Trucha("Trucha", 120, 180) for _ in range(n_truchas)]
        self.tiburones = [Tiburon("Tiburon", 200, 30) for _ in range(n_tiburones)]
        
    def simular_turno_ia(self):
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

        # Peces
        for pez in self.peces:
            pez.update_decision_turno(listas_de_seres)
            for planta in self.plantas:
                if pez.rect.colliderect(planta.rect) and planta not in plantas_comidas:
                    energia_ganada = pez.comer(planta)
                    if energia_ganada > 0:
                        # --- (IDEA 9) Evento de baja importancia ---
                        self.eventos_visuales.append(('comer_pez', pez.rect.center, energia_ganada))
                    plantas_comidas.append(planta)
                    break
            cria = pez.reproducir()
            if cria:
                nuevas_crias_peces.append(cria)
                self.eventos_visuales.append(('nacer', cria.rect.center))
            if pez.ha_muerto():
                peces_muertos.append(pez)
                # --- (IDEA 9) Evento de alta importancia ---
                self.eventos_visuales.append(('morir', pez.rect.center))

        # Truchas
        for trucha in self.truchas:
            trucha.update_decision_turno(listas_de_seres)
            for pez in self.peces:
                if pez not in peces_muertos and trucha.rect.colliderect(pez.rect):
                    energia_ganada = trucha.comer(pez)
                    if energia_ganada > 0:
                        # --- (IDEA 9) Evento de alta importancia ---
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

        # Tiburones
        for tiburon in self.tiburones:
            tiburon.update_decision_turno(listas_de_seres)
            for trucha in self.truchas:
                if trucha not in truchas_muertas and tiburon.rect.colliderect(trucha.rect):
                    energia_ganada = tiburon.comer(trucha)
                    if energia_ganada > 0:
                        # --- (IDEA 9) Evento de alta importancia ---
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

        # Limpieza
        set_peces_muertos = set(peces_muertos)
        set_truchas_muertas = set(truchas_muertas)
        set_tiburones_muertos = set(tiburones_muertos)
        set_plantas_comidas = set(plantas_comidas)

        self.peces = [p for p in self.peces if p not in set_peces_muertos]
        self.truchas = [t for t in self.truchas if t not in set_truchas_muertas]
        self.tiburones = [t for t in self.tiburones if t not in set_tiburones_muertos]
        self.plantas = [p for p in self.plantas if p not in set_plantas_comidas]

        # Adición
        self.peces.extend(nuevas_crias_peces)
        self.truchas.extend(nuevas_crias_truchas)
        self.tiburones.extend(nuevas_crias_tiburones)

        if random.random() < 0.8:
            self.plantas.append(Planta("Alga", 20))

    def actualizar_movimiento_frame(self):
        # Particionamiento espacial para reducir vecinos por entidad
        todos = self.peces + self.truchas + self.tiburones
        if not todos:
            return
        c = GRID_CELDA
        celdas = {}
        for a in todos:
            cx = int(a.pos_x) // c
            cy = int(a.pos_y) // c
            celdas.setdefault((cx, cy), []).append(a)

        # Radio maximo para vecinos (para separar y boids)
        vecino_r = 96.0
        vecino_r2 = vecino_r * vecino_r

        for a in todos:
            cx = int(a.pos_x) // c
            cy = int(a.pos_y) // c
            vecinos = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    lista = celdas.get((cx + dx, cy + dy))
                    if not lista:
                        continue
                    for o in lista:
                        if o is a:
                            continue
                        # Filtrar por distancia
                        ox = o.pos_x + o.rect.width * 0.5
                        oy = o.pos_y + o.rect.height * 0.5
                        sx = a.pos_x + a.rect.width * 0.5
                        sy = a.pos_y + a.rect.height * 0.5
                        ddx = sx - ox
                        ddy = sy - oy
                        if ddx*ddx + ddy*ddy <= vecino_r2:
                            vecinos.append(o)
            a.update_movimiento_frame(vecinos)

    # --- Estadisticas y probabilidad de supervivencia ---
    def calcular_prob_supervivencia(self):
        """Devuelve (especie_top, scores_dict) segun una heuristica simple.
        Las claves del diccionario son: 'peces', 'truchas', 'tiburones'.
        """
        np_ = len(self.peces)
        nt_ = len(self.truchas)
        nT_ = len(self.tiburones)
        npl_ = len(self.plantas)

        def avg_energy(lst, denom):
            if not lst:
                return 0.0
            s = 0.0
            for a in lst:
                try:
                    s += float(a.energia)
                except Exception:
                    pass
            return min(1.0, max(0.0, (s / max(1.0, len(lst) * float(denom)))))

        def avg_expectancy(lst):
            if not lst:
                return 0.0
            s = 0.0
            for a in lst:
                try:
                    rest = max(0.0, float(a.tiempo_vida - a.edad))
                    s += rest / max(1.0, float(a.tiempo_vida))
                except Exception:
                    pass
            return min(1.0, max(0.0, s / len(lst)))

        def pop_norm(n, k):
            return n / float(n + k) if n >= 0 else 0.0

        # Peces
        peces_pop = pop_norm(np_, 10)
        peces_energy = avg_energy(self.peces, 150)
        peces_expect = avg_expectancy(self.peces)
        peces_resource = min(1.0, npl_ / float(max(1, int(0.8 * max(1, np_))))) if np_ > 0 else (1.0 if npl_ > 0 else 0.0)
        peces_risk = min(1.0, (nt_ + nT_) / float(max(1, np_)))
        score_peces = (
            0.25 * peces_pop +
            0.30 * peces_energy +
            0.20 * peces_expect +
            0.25 * peces_resource -
            0.15 * peces_risk
        )

        # Truchas
        truchas_pop = pop_norm(nt_, 6)
        truchas_energy = avg_energy(self.truchas, 240)
        truchas_expect = avg_expectancy(self.truchas)
        truchas_resource = min(1.0, np_ / float(max(1, 2 * max(1, nt_)))) if nt_ > 0 else (1.0 if np_ > 0 else 0.0)
        truchas_risk = min(1.0, nT_ / float(max(1, nt_)))
        score_truchas = (
            0.25 * truchas_pop +
            0.30 * truchas_energy +
            0.20 * truchas_expect +
            0.25 * truchas_resource -
            0.18 * truchas_risk
        )

        # Tiburones (depredador tope: riesgo reducido)
        tib_pop = pop_norm(nT_, 4)
        tib_energy = avg_energy(self.tiburones, 320)
        tib_expect = avg_expectancy(self.tiburones)
        tib_resource = min(1.0, nt_ / float(max(1, 2 * max(1, nT_)))) if nT_ > 0 else (1.0 if nt_ > 0 else 0.0)
        tib_risk = 0.05 if nT_ > 0 else 0.0  # casi nulo
        score_tiburones = (
            0.30 * tib_pop +
            0.35 * tib_energy +
            0.20 * tib_expect +
            0.35 * tib_resource -
            0.10 * tib_risk
        )

        scores = {
            'peces': max(0.0, min(1.0, score_peces)),
            'truchas': max(0.0, min(1.0, score_truchas)),
            'tiburones': max(0.0, min(1.0, score_tiburones)),
        }
        especie_top = max(scores, key=scores.get) if scores else 'peces'
        return especie_top, scores
