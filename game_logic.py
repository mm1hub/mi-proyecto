"""
Lógica central del ecosistema.
Contiene todas las entidades y sus reglas de comportamiento.
Versión mejorada con cardúmenes, caza en grupo y persecución optimizada.
"""

import pygame
import random
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Any

import config as cfg


class Entity(ABC):
    """Clase base para todas las entidades del juego."""

    def __init__(self, x: float, y: float, width: int, height: int, name: str):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.name = name
        self.target_x = float(x)
        self.target_y = float(y)
        self.rect = pygame.Rect(int(x), int(y), width, height)

    def update_position(self):
        """Actualiza el rectángulo con la posición actual."""
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def clamp_to_bounds(self):
        """Mantiene a la entidad dentro del área de juego."""
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))
        self.update_position()

    def move_towards_target(self, speed: float) -> bool:
        """
        Mueve la entidad hacia su objetivo, respetando límites.
        Devuelve True si ya llegó.
        """
        # Limitar el objetivo al área de juego
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.target_x = max(0, min(self.target_x, max_x))
        self.target_y = max(0, min(self.target_y, max_y))

        dx = self.target_x - self.x
        dy = self.target_y - self.y

        distance = math.hypot(dx, dy)

        # Si está muy cerca, la dejamos exactamente en el objetivo
        if distance < speed or distance < 0.5:
            self.x = self.target_x
            self.y = self.target_y
            self.clamp_to_bounds()
            # Actualizar dirección si es un animal
            if hasattr(self, "direction") and dx != 0:
                self.direction = 1 if dx > 0 else -1
            return True

        if distance > 0:
            self.x += (dx / distance) * speed
            self.y += (dy / distance) * speed

        # Actualizar dirección según desplazamiento
        if hasattr(self, "direction") and dx != 0:
            self.direction = 1 if dx > 0 else -1

        self.clamp_to_bounds()
        return False

    def set_random_position(self):
        """Establece una posición aleatoria dentro del área de juego."""
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.x = random.randint(0, max(0, max_x))
        self.y = random.randint(0, max(0, max_y))
        self.target_x = self.x
        self.target_y = self.y
        self.update_position()


class Animal(Entity):
    """Clase base para animales con IA."""

    def __init__(
        self,
        x: float,
        y: float,
        width: int,
        height: int,
        name: str,
        energy: float,
        max_energy: float,
        lifespan: int,
    ):
        super().__init__(x, y, width, height, name)

        self.energy = energy
        self.max_energy = max_energy
        self.lifespan = lifespan
        self.age = 0

        # Velocidad base (cada especie la redefine)
        self.base_speed = random.uniform(0.5, 1.5)
        self.speed = self.base_speed
        self.base_consumption = 2.0
        self.consumption = self.base_consumption
        self.direction = 1  # 1 = derecha, -1 = izquierda

        # Estado de IA
        self.state = "idle"
        self.target_entity: Optional[Entity] = None

        # Multiplicador de la estación actual (para poder reutilizarlo)
        self.season_move_mult = 1.0

    def update(self, delta_time: float, ecosystem: "Ecosystem"):
        """Actualiza el estado del animal."""
        # Aplicar modificadores por estación (instinto de supervivencia ambiental)
        self.apply_season_modifiers(ecosystem)

        # Consumo de energía y envejecimiento
        self.energy = max(0, self.energy - self.consumption * delta_time)
        self.age += delta_time

        # Morir si es necesario
        if self.is_dead():
            return False

        # Ejecutar lógica de IA
        self.decide_action(ecosystem)

        # Moverse hacia el objetivo
        if self.state != "idle":
            self.move_towards_target(self.speed * delta_time * 60)

        return True

    def apply_season_modifiers(self, ecosystem: "Ecosystem"):
        """Ajusta velocidad y consumo según la estación."""
        season_name = ecosystem.time_system.get_season()
        season_cfg = cfg.SEASONS_CONFIG.get(season_name, {})
        modifiers = season_cfg.get("modifiers", {})

        self.season_move_mult = modifiers.get("movement", 1.0)
        cons_mult = modifiers.get("energy_consumption", 1.0)

        self.speed = self.base_speed * self.season_move_mult
        self.consumption = self.base_consumption * cons_mult

    def is_dead(self) -> bool:
        """Verifica si el animal ha muerto."""
        return self.energy <= 0 or self.age >= self.lifespan

    @abstractmethod
    def decide_action(self, ecosystem: "Ecosystem"):
        """Decide la siguiente acción (implementado por cada especie)."""
        pass

    @abstractmethod
    def can_eat(self, other: Entity) -> bool:
        """Determina si puede comer a otra entidad."""
        pass

    @abstractmethod
    def eat(self, other: Entity) -> float:
        """Come a otra entidad y retorna energía obtenida."""
        pass

    @abstractmethod
    def can_reproduce(self) -> bool:
        """Determina si puede reproducirse."""
        pass

    @abstractmethod
    def reproduce(self) -> Optional["Animal"]:
        """Intenta reproducirse."""
        pass


class Plant(Entity):
    """Planta estática que sirve de alimento."""

    def __init__(self, x: float, y: float, name: str = "Alga"):
        super().__init__(x, y, 14, 14, name)
        self.energy_value = 20.0
        self.growth = 100  # 0-100

    def consume(self) -> float:
        """Consume la planta y retorna su energía."""
        energy = self.energy_value * (self.growth / 100.0)
        self.growth = 0
        return energy

    def grow(self, delta_time: float):
        """La planta crece con el tiempo."""
        self.growth = min(100, self.growth + delta_time * 10)

    def is_fully_grown(self) -> bool:
        """Verifica si la planta está completamente crecida."""
        return self.growth >= 100


class Fish(Animal):
    """Pez herbívoro que come plantas y se mueve en cardúmenes."""

    def __init__(self, x: float, y: float, name: str = "Pejerrey"):
        super().__init__(x, y, 20, 20, name, energy=70, max_energy=100, lifespan=120)
        # Velocidad parametrizada
        self.base_speed = random.uniform(cfg.FISH_BASE_SPEED_MIN, cfg.FISH_BASE_SPEED_MAX)
        self.speed = self.base_speed
        self.consumption = 1.0

    def decide_action(self, ecosystem: "Ecosystem"):
        """Lógica de IA del pez."""

        # 1) Instinto de supervivencia: huir de depredadores cercanos
        predators = ecosystem.get_nearby_predators(self, 150)
        if predators:
            predator = predators[0]
            dx = self.x - predator.x
            dy = self.y - predator.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                flee_distance = 120
                self.target_x = self.x + (dx / distance) * flee_distance
                self.target_y = self.y + (dy / distance) * flee_distance
                self.state = "fleeing"
                return

        # 2) Hambre: buscar plantas
        if self.energy < self.max_energy * 0.3:
            plants = ecosystem.get_nearby_plants(self, 120)
            if plants:
                plant = plants[0]
                self.target_x = plant.x
                self.target_y = plant.y
                self.state = "eating"
                return

        # 3) Comportamiento de cardumen (boids muy simplificado)
        school = ecosystem.get_nearby_fish(self, cfg.FISH_SCHOOL_RADIUS)
        if len(school) >= cfg.FISH_SCHOOL_MIN_NEIGHBORS:
            # Centro del grupo
            avg_x = sum(f.x for f in school) / len(school)
            avg_y = sum(f.y for f in school) / len(school)

            # Separación si hay peces demasiado cerca
            sep_x = 0.0
            sep_y = 0.0
            for other in school:
                dx = self.x - other.x
                dy = self.y - other.y
                dist = math.hypot(dx, dy)
                if 0 < dist < cfg.FISH_SEPARATION_DISTANCE:
                    sep_x += dx / dist
                    sep_y += dy / dist

            # Mezclar cohesión (ir al centro) y separación
            target_x = self.x
            target_y = self.y

            # Cohesión
            target_x += (avg_x - self.x) * 0.4
            target_y += (avg_y - self.y) * 0.4

            # Separación
            target_x += sep_x * 25
            target_y += sep_y * 25

            self.target_x = target_x
            self.target_y = target_y
            self.state = "schooling"
            return

        # 4) Movimiento aleatorio suave si no hay nada especial
        if random.random() < 0.05:
            self.target_x = self.x + random.randint(-60, 60)
            self.target_y = self.y + random.randint(-40, 40)
            self.state = "moving"

    def can_eat(self, other: Entity) -> bool:
        return isinstance(other, Plant)

    def eat(self, other: Entity) -> float:
        if not self.can_eat(other):
            return 0.0

        energy = other.consume()
        self.energy = min(self.max_energy, self.energy + energy)
        self.state = "idle"
        return energy

    def can_reproduce(self) -> bool:
        return self.energy > self.max_energy * 0.7 and self.age > 3 and random.random() < 0.1

    def reproduce(self) -> Optional["Fish"]:
        if not self.can_reproduce():
            return None

        # Coste de reproducción
        self.energy -= 30

        # Crear cría
        baby = Fish(self.x, self.y)
        baby.energy = 50
        return baby


class Trout(Animal):
    """Trucha que come peces y puede cazar en grupo."""

    def __init__(self, x: float, y: float, name: str = "Trucha"):
        super().__init__(x, y, 35, 35, name, energy=120, max_energy=180, lifespan=180)
        # Velocidad parametrizada
        self.base_speed = random.uniform(cfg.TROUT_BASE_SPEED_MIN, cfg.TROUT_BASE_SPEED_MAX)
        self.speed = self.base_speed
        self.consumption = 1.5

    def decide_action(self, ecosystem: "Ecosystem"):
        """Lógica de IA de la trucha."""

        # Instinto de supervivencia: huir de tiburones
        sharks = ecosystem.get_nearby_sharks(self, cfg.TROUT_ESCAPE_RADAR)
        if sharks:
            shark = sharks[0]
            dx = self.x - shark.x
            dy = self.y - shark.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                flee_distance = 140
                self.target_x = self.x + (dx / distance) * flee_distance
                self.target_y = self.y + (dy / distance) * flee_distance
                # Aumenta la velocidad cuando está escapando
                self.speed = (
                    self.base_speed * self.season_move_mult * cfg.TROUT_ESCAPE_SPEED_MULTIPLIER
                )
                self.state = "fleeing"
                return
        else:
            # Si no está huyendo, volver a la velocidad "normal" de la estación
            self.speed = self.base_speed * self.season_move_mult

        # Hambre: cazar peces, individual o en grupo
        hungry = self.energy < self.max_energy * 0.45

        # Si ya tiene objetivo válido, seguirlo
        if hungry and isinstance(self.target_entity, Fish) and self.target_entity in ecosystem.fish:
            target: Optional[Fish] = self.target_entity  # type: ignore[assignment]
        elif hungry:
            fishes = ecosystem.get_nearby_fish(self, 260)
            target = fishes[0] if fishes else None
            self.target_entity = target
        else:
            target = None

        if hungry and target is not None:
            # Ver cuántas truchas aliadas hay cerca
            allies = ecosystem.get_nearby_trout(self, cfg.TROUT_PACK_RADIUS)

            if len(allies) >= cfg.TROUT_MIN_ALLIES_FOR_PACK:
                # Formar grupo de hasta TROUT_MAX_PACK_SIZE (incluye al líder)
                pack = ecosystem.form_trout_pack(
                    self,
                    cfg.TROUT_PACK_RADIUS,
                    cfg.TROUT_MAX_PACK_SIZE,
                )
                for mate in pack:
                    mate.target_entity = target
                    mate.target_x = target.x
                    mate.target_y = target.y
                    mate.state = "hunting"
            else:
                # Ataca de forma individual
                self.target_entity = target
                self.target_x = target.x
                self.target_y = target.y
                self.state = "hunting"

            return

        # Si no está hambrienta, nadar cerca de otras truchas (ligero cardumen)
        allies = ecosystem.get_nearby_trout(self, 120)
        if allies:
            avg_x = sum(t.x for t in allies) / len(allies)
            avg_y = sum(t.y for t in allies) / len(allies)
            self.target_x = avg_x + random.randint(-30, 30)
            self.target_y = avg_y + random.randint(-20, 20)
            self.state = "moving"
            return

        # Movimiento aleatorio si está sola
        if random.random() < 0.03:
            self.target_x = self.x + random.randint(-80, 80)
            self.target_y = self.y + random.randint(-60, 60)
            self.state = "moving"

    def can_eat(self, other: Entity) -> bool:
        return isinstance(other, Fish)

    def eat(self, other: Entity) -> float:
        if not self.can_eat(other):
            return 0.0

        energy = min(35, getattr(other, "energy", 60) * 0.5)
        self.energy = min(self.max_energy, self.energy + energy)
        self.state = "idle"
        self.target_entity = None
        return energy

    def can_reproduce(self) -> bool:
        return self.energy > self.max_energy * 0.6 and self.age > 6 and random.random() < 0.08

    def reproduce(self) -> Optional["Trout"]:
        if not self.can_reproduce():
            return None

        self.energy -= 50
        baby = Trout(self.x, self.y)
        baby.energy = 100
        return baby


class Shark(Animal):
    """Tiburón que come truchas con persecución mejorada."""

    def __init__(self, x: float, y: float, name: str = "Tiburón"):
        super().__init__(x, y, 45, 45, name, energy=200, max_energy=300, lifespan=300)
        # Velocidad parametrizada
        self.base_speed = random.uniform(cfg.SHARK_BASE_SPEED_MIN, cfg.SHARK_BASE_SPEED_MAX)
        self.speed = self.base_speed
        self.consumption = 0.8

    def decide_action(self, ecosystem: "Ecosystem"):
        """Lógica de IA del tiburón (persecución coherente)."""

        # Cuán hambriento está (0=sin energía, 1=lleno)
        fullness = self.energy / self.max_energy

        # Radios de caza dinámicos
        if fullness < cfg.SHARK_HUNGER_THRESHOLD:
            hunt_radius = cfg.SHARK_HUNT_RADIUS_HUNGRY
        else:
            hunt_radius = cfg.SHARK_HUNT_RADIUS_RELAXED

        target: Optional[Trout] = None

        # ¿Tiene ya una trucha fijada?
        if isinstance(self.target_entity, Trout) and self.target_entity in ecosystem.trout:
            # ¿Sigue razonablemente cerca?
            dx = self.target_entity.x - self.x
            dy = self.target_entity.y - self.y
            dist = math.hypot(dx, dy)
            if dist <= cfg.SHARK_TARGET_PERSISTENCE:
                target = self.target_entity

        # Si no hay objetivo válido, buscar la trucha más cercana
        if target is None:
            trouts = ecosystem.get_nearby_trout(self, hunt_radius)
            if trouts:
                target = trouts[0]  # ya vienen ordenadas por distancia
                self.target_entity = target

        if target is not None:
            # Persecución con ligera anticipación
            dx = target.x - self.x
            dy = target.y - self.y
            distance = math.hypot(dx, dy) or 1.0

            lead_factor = 0.3  # cuanto "se adelanta" al movimiento
            self.target_x = target.x + (dx / distance) * lead_factor * 40
            self.target_y = target.y + (dy / distance) * lead_factor * 20
            self.state = "hunting"
            return

        # Si no hay presas cercanas, patrullar por el mapa
        if random.random() < 0.02:
            # Patrullar más hacia la zona central
            center_x = cfg.GAME_AREA_WIDTH / 2
            center_y = cfg.SCREEN_HEIGHT / 2
            self.target_x = center_x + random.randint(-300, 300)
            self.target_y = center_y + random.randint(-200, 200)
            self.state = "patrolling"

    def can_eat(self, other: Entity) -> bool:
        return isinstance(other, Trout)

    def eat(self, other: Entity) -> float:
        if not self.can_eat(other):
            return 0.0

        energy = min(85, getattr(other, "energy", 100) * 0.7)
        self.energy = min(self.max_energy, self.energy + energy)
        self.state = "idle"
        self.target_entity = None
        return energy

    def can_reproduce(self) -> bool:
        return self.energy > self.max_energy * 0.7 and self.age > 8 and random.random() < 0.05

    def reproduce(self) -> Optional["Shark"]:
        if not self.can_reproduce():
            return None

        self.energy -= 80
        baby = Shark(self.x, self.y)
        baby.energy = 150
        return baby


class TimeSystem:
    """Sistema que maneja el tiempo y estaciones."""

    def __init__(self):
        self.turn = 0
        self.day = 1
        self.season_index = 0
        self.day_progress = 0.0

    def update(self, delta_turns: float = 1.0):
        """Actualiza el estado del tiempo."""
        self.turn += delta_turns
        self.day_progress = (self.turn % cfg.DAY_CYCLE_TURNS) / cfg.DAY_CYCLE_TURNS
        self.day = int(self.turn // cfg.DAY_CYCLE_TURNS) + 1
        self.season_index = ((self.day - 1) // cfg.DAYS_PER_SEASON) % len(cfg.SEASONS_ORDER)

    def get_season(self) -> str:
        """Obtiene la estación actual."""
        return cfg.SEASONS_ORDER[self.season_index]

    def get_time_of_day(self) -> str:
        """Obtiene la fase del día."""
        if self.day_progress < cfg.DAWN_FRACTION:
            return "amanecer"
        elif self.day_progress < 0.5:
            return "dia"
        elif self.day_progress < cfg.DUSK_FRACTION:
            return "atardecer"
        else:
            return "noche"

    def is_night(self) -> bool:
        """Verifica si es de noche."""
        return self.get_time_of_day() == "noche"

    def get_light_factor(self) -> float:
        """Obtiene el factor de luz para efectos visuales."""
        if self.is_night():
            return 0.1
        elif self.day_progress < cfg.DAWN_FRACTION:
            return 0.1 + 0.9 * (self.day_progress / cfg.DAWN_FRACTION)
        elif self.day_progress < 0.5:
            return 1.0
        else:
            return 1.0 - 0.9 * ((self.day_progress - 0.5) / (cfg.DUSK_FRACTION - 0.5))


class Ecosystem:
    """Sistema principal que maneja todas las entidades."""

    def __init__(self):
        self.plants: List[Plant] = []
        self.fish: List[Fish] = []
        self.trout: List[Trout] = []
        self.sharks: List[Shark] = []

        self.time_system = TimeSystem()
        self.events: List[Dict] = []
        self.turn_count = 0

        # Estado
        self.paused = False
        self.simulation_speed = 1.0

    def initialize(self, population_config: Dict[str, int] = None):
        """Inicializa el ecosistema con población inicial."""
        config = population_config or cfg.DEFAULT_POPULATION

        # Limpiar listas
        self.plants.clear()
        self.fish.clear()
        self.trout.clear()
        self.sharks.clear()
        self.events.clear()

        # Crear plantas
        for _ in range(config["plantas"]):
            plant = Plant(0, 0)
            plant.set_random_position()
            self.plants.append(plant)

        # Crear peces
        for _ in range(config["peces"]):
            fish = Fish(0, 0)
            fish.set_random_position()
            self.fish.append(fish)

        # Crear truchas
        for _ in range(config["truchas"]):
            trout = Trout(0, 0)
            trout.set_random_position()
            self.trout.append(trout)

        # Crear tiburones
        for _ in range(config["tiburones"]):
            shark = Shark(0, 0)
            shark.set_random_position()
            self.sharks.append(shark)

        # Reiniciar tiempo
        self.time_system = TimeSystem()
        self.turn_count = 0

    def update(self, delta_time: float):
        """Actualiza el estado del ecosistema."""
        if self.paused:
            return

        # Actualizar tiempo
        self.time_system.update(delta_time * 10)  # Escalar delta_time para turnos

        # Limpiar eventos del frame anterior
        self.events.clear()

        # Actualizar plantas
        for plant in self.plants:
            plant.grow(delta_time)

        # Actualizar y procesar animales
        self._update_animals(delta_time)

        # Procesar interacciones (comer)
        self._process_interactions()

        # Balancear poblaciones
        self._balance_populations()

        # Registrar estadísticas
        self.turn_count += 1

    def _update_animals(self, delta_time: float):
        """Actualiza todos los animales."""
        # Peces
        dead_fish: List[Fish] = []
        new_fish: List[Fish] = []

        for fish in self.fish:
            if not fish.update(delta_time, self):
                dead_fish.append(fish)
            elif fish.can_reproduce():
                baby = fish.reproduce()
                if baby:
                    baby.set_random_position()
                    new_fish.append(baby)
                    self.events.append(
                        {"type": "birth", "position": (fish.x, fish.y), "species": "pez"}
                    )

        # Truchas
        dead_trout: List[Trout] = []
        new_trout: List[Trout] = []

        for trout in self.trout:
            if not trout.update(delta_time, self):
                dead_trout.append(trout)
            elif trout.can_reproduce():
                baby = trout.reproduce()
                if baby:
                    baby.set_random_position()
                    new_trout.append(baby)
                    self.events.append(
                        {"type": "birth", "position": (trout.x, trout.y), "species": "trucha"}
                    )

        # Tiburones
        dead_sharks: List[Shark] = []
        new_sharks: List[Shark] = []

        for shark in self.sharks:
            if not shark.update(delta_time, self):
                dead_sharks.append(shark)
            elif shark.can_reproduce():
                baby = shark.reproduce()
                if baby:
                    baby.set_random_position()
                    new_sharks.append(baby)
                    self.events.append(
                        {"type": "birth", "position": (shark.x, shark.y), "species": "tiburon"}
                    )

        # Eliminar muertos
        for fish in dead_fish:
            if fish in self.fish:
                self.fish.remove(fish)
                self.events.append({"type": "death", "position": (fish.x, fish.y)})

        for trout in dead_trout:
            if trout in self.trout:
                self.trout.remove(trout)
                self.events.append({"type": "death", "position": (trout.x, trout.y)})

        for shark in dead_sharks:
            if shark in self.sharks:
                self.sharks.remove(shark)
                self.events.append({"type": "death", "position": (shark.x, shark.y)})

        # Añadir nuevos
        self.fish.extend(new_fish)
        self.trout.extend(new_trout)
        self.sharks.extend(new_sharks)

    def _process_interactions(self):
        """Procesa interacciones entre entidades."""
        # Peces comen plantas
        for fish in self.fish:
            for plant in self.plants[:]:  # Copia para modificar
                if fish.rect.colliderect(plant.rect):
                    energy = fish.eat(plant)
                    if energy > 0:
                        if plant in self.plants:
                            self.plants.remove(plant)
                        self.events.append(
                            {
                                "type": "eat",
                                "position": (fish.x, fish.y),
                                "energy": energy,
                                "eater": "pez",
                            }
                        )
                        break

        # Truchas comen peces
        for trout in self.trout:
            for fish in self.fish[:]:
                if trout.rect.colliderect(fish.rect):
                    energy = trout.eat(fish)
                    if energy > 0:
                        if fish in self.fish:
                            self.fish.remove(fish)
                        self.events.append(
                            {
                                "type": "eat",
                                "position": (trout.x, trout.y),
                                "energy": energy,
                                "eater": "trucha",
                            }
                        )
                        break

        # Tiburones comen truchas
        for shark in self.sharks:
            for trout in self.trout[:]:
                if shark.rect.colliderect(trout.rect):
                    energy = shark.eat(trout)
                    if energy > 0:
                        if trout in self.trout:
                            self.trout.remove(trout)
                        self.events.append(
                            {
                                "type": "eat",
                                "position": (shark.x, shark.y),
                                "energy": energy,
                                "eater": "tiburon",
                            }
                        )
                        break

    def _balance_populations(self):
        """Mantiene las poblaciones dentro de límites."""
        # Plantas
        if len(self.plants) < cfg.POPULATION_LIMITS["plantas"]["min"]:
            deficit = cfg.POPULATION_LIMITS["plantas"]["min"] - len(self.plants)
            for _ in range(deficit):
                plant = Plant(0, 0)
                plant.set_random_position()
                self.plants.append(plant)

        elif len(self.plants) > cfg.POPULATION_LIMITS["plantas"]["max"]:
            excess = len(self.plants) - cfg.POPULATION_LIMITS["plantas"]["max"]
            self.plants = self.plants[:-excess] if excess > 0 else []

    # ------------------------------------------------------------------ #
    #   UTILIDADES DE BÚSQUEDA Y AGRUPACIÓN
    # ------------------------------------------------------------------ #

    def get_nearby_entities(
        self, entity: Entity, radius: float, entity_list: List[Entity]
    ) -> List[Entity]:
        """Obtiene entidades cercanas a una posición, ordenadas por distancia."""
        nearby: List[Entity] = []
        for other in entity_list:
            if other == entity:
                continue

            dx = other.x - entity.x
            dy = other.y - entity.y
            distance = math.hypot(dx, dy)

            if distance <= radius:
                nearby.append(other)

        nearby.sort(key=lambda e: math.hypot(e.x - entity.x, e.y - entity.y))
        return nearby

    def get_nearby_plants(self, entity: Entity, radius: float) -> List[Plant]:
        return self.get_nearby_entities(entity, radius, self.plants)  # type: ignore

    def get_nearby_fish(self, entity: Entity, radius: float) -> List[Fish]:
        return self.get_nearby_entities(entity, radius, self.fish)  # type: ignore

    def get_nearby_trout(self, entity: Entity, radius: float) -> List[Trout]:
        return self.get_nearby_entities(entity, radius, self.trout)  # type: ignore

    def get_nearby_sharks(self, entity: Entity, radius: float) -> List[Shark]:
        return self.get_nearby_entities(entity, radius, self.sharks)  # type: ignore

    def get_nearby_predators(self, entity: Entity, radius: float) -> List[Animal]:
        """Obtiene depredadores cercanos."""
        predators: List[Animal] = []
        if isinstance(entity, Fish):
            predators.extend(self.get_nearby_trout(entity, radius))
            predators.extend(self.get_nearby_sharks(entity, radius))
        elif isinstance(entity, Trout):
            predators.extend(self.get_nearby_sharks(entity, radius))
        return predators

    def form_trout_pack(self, leader: Trout, radius: float, max_size: int) -> List[Trout]:
        """
        Forma un pequeño grupo de truchas alrededor de un líder.
        Incluye siempre al líder y añade las más cercanas hasta max_size.
        """
        allies = self.get_nearby_trout(leader, radius)
        pack: List[Trout] = [leader]
        for t in allies:
            if len(pack) >= max_size:
                break
            pack.append(t)
        return pack

    # ------------------------------------------------------------------ #

    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales."""
        return {
            "plants": len(self.plants),
            "fish": len(self.fish),
            "trout": len(self.trout),
            "sharks": len(self.sharks),
            "turn": self.turn_count,
            "season": self.time_system.get_season(),
            "day": self.time_system.day,
            "time_of_day": self.time_system.get_time_of_day(),
            "day_progress": self.time_system.day_progress,
            "season_progress": (self.time_system.day % cfg.DAYS_PER_SEASON)
            / cfg.DAYS_PER_SEASON,
            "is_night": self.time_system.is_night(),
            "light_factor": self.time_system.get_light_factor(),
        }

    def set_paused(self, paused: bool):
        """Pausa o reanuda la simulación."""
        self.paused = paused
