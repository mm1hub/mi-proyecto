"""
Lógica central del ecosistema.
Incluye serialización completa (JSON) para guardado/carga.
"""

import pygame
import random
import math
from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Optional, Any

import config as cfg


# ==============================
#        ENTIDADES BASE
# ==============================

class Entity(ABC):
    """Clase base para todas las entidades del juego."""

    def __init__(self, x: float, y: float, width: int, height: int, name: str):
        self.eid: int = -1  # asignado por Ecosystem
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.name = name

        self.target_x = float(x)
        self.target_y = float(y)
        self.rect = pygame.Rect(int(x), int(y), width, height)

    def update_position(self):
        self.rect.x = int(self.x)
        self.rect.y = int(self.y)

    def clamp_to_bounds(self):
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.x = max(0, min(self.x, max_x))
        self.y = max(0, min(self.y, max_y))
        self.update_position()

    def move_towards_target(self, speed: float) -> bool:
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.target_x = max(0, min(self.target_x, max_x))
        self.target_y = max(0, min(self.target_y, max_y))

        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.hypot(dx, dy)

        if dist < speed or dist < 0.5:
            self.x = self.target_x
            self.y = self.target_y
            self.clamp_to_bounds()
            if hasattr(self, "direction") and dx != 0:
                self.direction = 1 if dx > 0 else -1
            return True

        if dist > 0:
            self.x += (dx / dist) * speed
            self.y += (dy / dist) * speed

        if hasattr(self, "direction") and dx != 0:
            self.direction = 1 if dx > 0 else -1

        self.clamp_to_bounds()
        return False

    def set_random_position(self):
        max_x = cfg.GAME_AREA_WIDTH - self.width
        max_y = cfg.SCREEN_HEIGHT - self.height
        self.x = random.randint(0, max(0, max_x))
        self.y = random.randint(0, max(0, max_y))
        self.target_x = self.x
        self.target_y = self.y
        self.update_position()

    # -------- SERIALIZACIÓN --------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.eid,
            "type": self.__class__.__name__,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "target_x": self.target_x,
            "target_y": self.target_y,
        }

    def load_common(self, data: Dict[str, Any]):
        self.name = data.get("name", self.name)
        self.x = float(data.get("x", self.x))
        self.y = float(data.get("y", self.y))
        self.target_x = float(data.get("target_x", self.x))
        self.target_y = float(data.get("target_y", self.y))
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

        self.energy = float(energy)
        self.max_energy = float(max_energy)
        self.lifespan = int(lifespan)
        self.age = 0.0

        self.base_speed = random.uniform(0.5, 1.5)
        self.speed = self.base_speed

        # IMPORTANTÍSIMO: estos deben ser coherentes por especie
        self.base_consumption = 2.0
        self.consumption = self.base_consumption

        self.direction = 1
        self.state = "idle"
        self.target_entity: Optional[Entity] = None

        self.season_move_mult = 1.0
        self._pending_target_id: Optional[int] = None  # para reconstrucción en load

    def apply_season_modifiers(self, ecosystem: "Ecosystem"):
        season_name = ecosystem.time_system.get_season()
        season_cfg = cfg.SEASONS_CONFIG.get(season_name, {})
        modifiers = season_cfg.get("modifiers", {})

        self.season_move_mult = float(modifiers.get("movement", 1.0))
        cons_mult = float(modifiers.get("energy_consumption", 1.0))

        self.speed = self.base_speed * self.season_move_mult
        self.consumption = self.base_consumption * cons_mult

    def update(self, delta_time: float, ecosystem: "Ecosystem") -> bool:
        self.apply_season_modifiers(ecosystem)

        self.energy = max(0.0, self.energy - self.consumption * delta_time)
        self.age += delta_time

        if self.is_dead():
            return False

        self.decide_action(ecosystem)

        if self.state != "idle":
            self.move_towards_target(self.speed * delta_time * 60)

        return True

    def is_dead(self) -> bool:
        return self.energy <= 0.0 or self.age >= self.lifespan

    @abstractmethod
    def decide_action(self, ecosystem: "Ecosystem"):
        pass

    @abstractmethod
    def can_eat(self, other: Entity) -> bool:
        pass

    @abstractmethod
    def eat(self, other: Entity) -> float:
        pass

    @abstractmethod
    def can_reproduce(self) -> bool:
        pass

    @abstractmethod
    def reproduce(self) -> Optional["Animal"]:
        pass

    # -------- SERIALIZACIÓN --------
    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update(
            {
                "energy": self.energy,
                "max_energy": self.max_energy,
                "lifespan": self.lifespan,
                "age": self.age,
                "base_speed": self.base_speed,
                "base_consumption": self.base_consumption,
                "direction": self.direction,
                "state": self.state,
                "target_id": self.target_entity.eid if self.target_entity else None,
            }
        )
        return base

    def load_animal_state(self, data: Dict[str, Any]):
        self.energy = float(data.get("energy", self.energy))
        self.max_energy = float(data.get("max_energy", self.max_energy))
        self.lifespan = int(data.get("lifespan", self.lifespan))
        self.age = float(data.get("age", self.age))

        self.base_speed = float(data.get("base_speed", self.base_speed))
        self.base_consumption = float(data.get("base_consumption", self.base_consumption))
        self.direction = int(data.get("direction", self.direction))
        self.state = data.get("state", self.state)

        # se recalculan en update(), pero dejamos consistente
        self.speed = self.base_speed
        self.consumption = self.base_consumption

        self._pending_target_id = data.get("target_id", None)


class Plant(Entity):
    def __init__(self, x: float, y: float, name: str = "Alga"):
        super().__init__(x, y, 14, 14, name)
        self.energy_value = 20.0
        self.growth = 100

    def consume(self) -> float:
        energy = self.energy_value * (self.growth / 100.0)
        self.growth = 0
        return energy

    def grow(self, delta_time: float):
        self.growth = min(100, self.growth + delta_time * 10)

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base["growth"] = self.growth
        return base

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Plant":
        p = cls(float(data.get("x", 0)), float(data.get("y", 0)), name=data.get("name", "Alga"))
        p.eid = int(data.get("id", -1))
        p.load_common(data)
        p.growth = int(data.get("growth", 100))
        return p


# ==============================
#          ESPECIES
# ==============================

class Fish(Animal):
    def __init__(self, x: float, y: float, name: str = "Pejerrey"):
        super().__init__(x, y, 20, 20, name, energy=70, max_energy=100, lifespan=120)
        self.base_speed = random.uniform(cfg.FISH_BASE_SPEED_MIN, cfg.FISH_BASE_SPEED_MAX)
        self.speed = self.base_speed

        self.base_consumption = 1.0
        self.consumption = self.base_consumption

    def decide_action(self, ecosystem: "Ecosystem"):
        predators = ecosystem.get_nearby_predators(self, 150)
        if predators:
            predator = predators[0]
            dx = self.x - predator.x
            dy = self.y - predator.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                flee_distance = 120
                self.target_x = self.x + (dx / dist) * flee_distance
                self.target_y = self.y + (dy / dist) * flee_distance
                self.state = "fleeing"
                return

        if self.energy < self.max_energy * 0.3:
            plants = ecosystem.get_nearby_plants(self, 120)
            if plants:
                plant = plants[0]
                self.target_x = plant.x
                self.target_y = plant.y
                self.state = "eating"
                self.target_entity = plant
                return

        school = ecosystem.get_nearby_fish(self, cfg.FISH_SCHOOL_RADIUS)
        if len(school) >= cfg.FISH_SCHOOL_MIN_NEIGHBORS:
            avg_x = sum(f.x for f in school) / len(school)
            avg_y = sum(f.y for f in school) / len(school)

            sep_x, sep_y = 0.0, 0.0
            for other in school:
                dx = self.x - other.x
                dy = self.y - other.y
                d = math.hypot(dx, dy)
                if 0 < d < cfg.FISH_SEPARATION_DISTANCE:
                    sep_x += dx / d
                    sep_y += dy / d

            target_x = self.x + (avg_x - self.x) * 0.4 + sep_x * 25
            target_y = self.y + (avg_y - self.y) * 0.4 + sep_y * 25

            self.target_x = target_x
            self.target_y = target_y
            self.state = "schooling"
            return

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
        self.target_entity = None
        return energy

    def can_reproduce(self) -> bool:
        return self.energy > self.max_energy * 0.7 and self.age > 3 and random.random() < 0.1

    def reproduce(self) -> Optional["Fish"]:
        if not self.can_reproduce():
            return None
        self.energy -= 30
        baby = Fish(self.x, self.y)
        baby.energy = 50
        return baby

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fish":
        f = cls(float(data.get("x", 0)), float(data.get("y", 0)), name=data.get("name", "Pejerrey"))
        f.eid = int(data.get("id", -1))
        f.load_common(data)
        f.load_animal_state(data)
        return f


class Trout(Animal):
    def __init__(self, x: float, y: float, name: str = "Trucha"):
        super().__init__(x, y, 35, 35, name, energy=120, max_energy=180, lifespan=180)
        self.base_speed = random.uniform(cfg.TROUT_BASE_SPEED_MIN, cfg.TROUT_BASE_SPEED_MAX)
        self.speed = self.base_speed

        self.base_consumption = 1.5
        self.consumption = self.base_consumption

    def decide_action(self, ecosystem: "Ecosystem"):
        # HUÍR si tiburón en radar (boost parametrizado)
        sharks = ecosystem.get_nearby_sharks(self, cfg.TROUT_ESCAPE_RADAR)
        if sharks:
            shark = sharks[0]
            dx = self.x - shark.x
            dy = self.y - shark.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                flee_distance = 140
                self.target_x = self.x + (dx / dist) * flee_distance
                self.target_y = self.y + (dy / dist) * flee_distance
                self.speed = self.base_speed * self.season_move_mult * cfg.TROUT_ESCAPE_SPEED_MULTIPLIER
                self.state = "fleeing"
                self.target_entity = None
                return
        else:
            self.speed = self.base_speed * self.season_move_mult

        hungry = self.energy < self.max_energy * 0.45

        # Mantener objetivo si sigue vivo
        target: Optional[Fish] = None
        if hungry and isinstance(self.target_entity, Fish) and self.target_entity in ecosystem.fish:
            target = self.target_entity
        elif hungry:
            fishes = ecosystem.get_nearby_fish(self, 260)
            target = fishes[0] if fishes else None
            self.target_entity = target
        else:
            self.target_entity = None

        if hungry and target is not None:
            allies = ecosystem.get_nearby_trout(self, cfg.TROUT_PACK_RADIUS)

            if len(allies) >= cfg.TROUT_MIN_ALLIES_FOR_PACK:
                pack = ecosystem.form_trout_pack(self, cfg.TROUT_PACK_RADIUS, cfg.TROUT_MAX_PACK_SIZE)
                for mate in pack:
                    mate.target_entity = target
                    mate.target_x = target.x
                    mate.target_y = target.y
                    mate.state = "hunting"
            else:
                self.target_x = target.x
                self.target_y = target.y
                self.state = "hunting"

            return

        # movimiento relajado cerca de otras truchas
        allies = ecosystem.get_nearby_trout(self, 120)
        if allies:
            avg_x = sum(t.x for t in allies) / len(allies)
            avg_y = sum(t.y for t in allies) / len(allies)
            self.target_x = avg_x + random.randint(-30, 30)
            self.target_y = avg_y + random.randint(-20, 20)
            self.state = "moving"
            return

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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trout":
        t = cls(float(data.get("x", 0)), float(data.get("y", 0)), name=data.get("name", "Trucha"))
        t.eid = int(data.get("id", -1))
        t.load_common(data)
        t.load_animal_state(data)
        return t


class Shark(Animal):
    def __init__(self, x: float, y: float, name: str = "Tiburón"):
        super().__init__(x, y, 45, 45, name, energy=200, max_energy=300, lifespan=300)
        self.base_speed = random.uniform(cfg.SHARK_BASE_SPEED_MIN, cfg.SHARK_BASE_SPEED_MAX)
        self.speed = self.base_speed

        self.base_consumption = 0.8
        self.consumption = self.base_consumption

    def decide_action(self, ecosystem: "Ecosystem"):
        fullness = self.energy / self.max_energy
        hunt_radius = cfg.SHARK_HUNT_RADIUS_HUNGRY if fullness < cfg.SHARK_HUNGER_THRESHOLD else cfg.SHARK_HUNT_RADIUS_RELAXED

        target: Optional[Trout] = None

        if isinstance(self.target_entity, Trout) and self.target_entity in ecosystem.trout:
            dx = self.target_entity.x - self.x
            dy = self.target_entity.y - self.y
            dist = math.hypot(dx, dy)
            if dist <= cfg.SHARK_TARGET_PERSISTENCE:
                target = self.target_entity

        if target is None:
            trouts = ecosystem.get_nearby_trout(self, hunt_radius)
            if trouts:
                target = trouts[0]
                self.target_entity = target

        if target is not None:
            dx = target.x - self.x
            dy = target.y - self.y
            dist = math.hypot(dx, dy) or 1.0

            lead_factor = 0.3
            self.target_x = target.x + (dx / dist) * lead_factor * 40
            self.target_y = target.y + (dy / dist) * lead_factor * 20
            self.state = "hunting"
            return

        if random.random() < 0.02:
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shark":
        s = cls(float(data.get("x", 0)), float(data.get("y", 0)), name=data.get("name", "Tiburón"))
        s.eid = int(data.get("id", -1))
        s.load_common(data)
        s.load_animal_state(data)
        return s


# ==============================
#         TIEMPO
# ==============================

class TimeSystem:
    def __init__(self):
        self.turn = 0.0
        self.day = 1
        self.season_index = 0
        self.day_progress = 0.0

    def _recalculate(self):
        self.day_progress = (self.turn % cfg.DAY_CYCLE_TURNS) / cfg.DAY_CYCLE_TURNS
        self.day = int(self.turn // cfg.DAY_CYCLE_TURNS) + 1
        self.season_index = ((self.day - 1) // cfg.DAYS_PER_SEASON) % len(cfg.SEASONS_ORDER)

    def update(self, delta_turns: float = 1.0):
        self.turn += float(delta_turns)
        self._recalculate()

    def get_season(self) -> str:
        return cfg.SEASONS_ORDER[self.season_index]

    def get_time_of_day(self) -> str:
        if self.day_progress < cfg.DAWN_FRACTION:
            return "amanecer"
        elif self.day_progress < 0.5:
            return "dia"
        elif self.day_progress < cfg.DUSK_FRACTION:
            return "atardecer"
        else:
            return "noche"

    def is_night(self) -> bool:
        return self.get_time_of_day() == "noche"

    def get_light_factor(self) -> float:
        if self.is_night():
            return 0.1
        elif self.day_progress < cfg.DAWN_FRACTION:
            return 0.1 + 0.9 * (self.day_progress / cfg.DAWN_FRACTION)
        elif self.day_progress < 0.5:
            return 1.0
        else:
            return 1.0 - 0.9 * ((self.day_progress - 0.5) / (cfg.DUSK_FRACTION - 0.5))

    def to_dict(self) -> Dict[str, Any]:
        return {"turn": self.turn}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeSystem":
        ts = cls()
        ts.turn = float(data.get("turn", 0.0))
        ts._recalculate()
        return ts


# ==============================
#        ECOSISTEMA
# ==============================

class Ecosystem:
    def __init__(self):
        self.plants: List[Plant] = []
        self.fish: List[Fish] = []
        self.trout: List[Trout] = []
        self.sharks: List[Shark] = []

        self.time_system = TimeSystem()
        self.events: List[Dict[str, Any]] = []
        self.turn_count = 0

        self.paused = False
        self.simulation_speed = 1.0

        self._next_entity_id = 1

    def _assign_id(self, e: Entity):
        if e.eid == -1:
            e.eid = self._next_entity_id
            self._next_entity_id += 1

    def initialize(self, population_config: Dict[str, int] = None):
        config = population_config or cfg.DEFAULT_POPULATION

        self.plants.clear()
        self.fish.clear()
        self.trout.clear()
        self.sharks.clear()
        self.events.clear()

        self._next_entity_id = 1

        for _ in range(config["plantas"]):
            p = Plant(0, 0)
            self._assign_id(p)
            p.set_random_position()
            self.plants.append(p)

        for _ in range(config["peces"]):
            f = Fish(0, 0)
            self._assign_id(f)
            f.set_random_position()
            self.fish.append(f)

        for _ in range(config["truchas"]):
            t = Trout(0, 0)
            self._assign_id(t)
            t.set_random_position()
            self.trout.append(t)

        for _ in range(config["tiburones"]):
            s = Shark(0, 0)
            self._assign_id(s)
            s.set_random_position()
            self.sharks.append(s)

        self.time_system = TimeSystem()
        self.turn_count = 0
        self.paused = False

    def update(self, delta_time: float):
        if self.paused:
            return

        self.time_system.update(delta_time * 10)
        self.events.clear()

        for plant in self.plants:
            plant.grow(delta_time)

        self._update_animals(delta_time)
        self._process_interactions()
        self._balance_populations()

        self.turn_count += 1

    def _update_animals(self, delta_time: float):
        dead_fish: List[Fish] = []
        new_fish: List[Fish] = []

        for fish in self.fish:
            if not fish.update(delta_time, self):
                dead_fish.append(fish)
            elif fish.can_reproduce():
                baby = fish.reproduce()
                if baby:
                    self._assign_id(baby)
                    baby.set_random_position()
                    new_fish.append(baby)
                    self.events.append({"type": "birth", "position": (fish.x, fish.y), "species": "pez"})

        dead_trout: List[Trout] = []
        new_trout: List[Trout] = []

        for trout in self.trout:
            if not trout.update(delta_time, self):
                dead_trout.append(trout)
            elif trout.can_reproduce():
                baby = trout.reproduce()
                if baby:
                    self._assign_id(baby)
                    baby.set_random_position()
                    new_trout.append(baby)
                    self.events.append({"type": "birth", "position": (trout.x, trout.y), "species": "trucha"})

        dead_sharks: List[Shark] = []
        new_sharks: List[Shark] = []

        for shark in self.sharks:
            if not shark.update(delta_time, self):
                dead_sharks.append(shark)
            elif shark.can_reproduce():
                baby = shark.reproduce()
                if baby:
                    self._assign_id(baby)
                    baby.set_random_position()
                    new_sharks.append(baby)
                    self.events.append({"type": "birth", "position": (shark.x, shark.y), "species": "tiburon"})

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

        self.fish.extend(new_fish)
        self.trout.extend(new_trout)
        self.sharks.extend(new_sharks)

    def _process_interactions(self):
        for fish in self.fish:
            for plant in self.plants[:]:
                if fish.rect.colliderect(plant.rect):
                    energy = fish.eat(plant)
                    if energy > 0:
                        if plant in self.plants:
                            self.plants.remove(plant)
                        self.events.append({"type": "eat", "position": (fish.x, fish.y), "energy": energy, "eater": "pez"})
                        break

        for trout in self.trout:
            for fish in self.fish[:]:
                if trout.rect.colliderect(fish.rect):
                    energy = trout.eat(fish)
                    if energy > 0:
                        if fish in self.fish:
                            self.fish.remove(fish)
                        self.events.append({"type": "eat", "position": (trout.x, trout.y), "energy": energy, "eater": "trucha"})
                        break

        for shark in self.sharks:
            for trout in self.trout[:]:
                if shark.rect.colliderect(trout.rect):
                    energy = shark.eat(trout)
                    if energy > 0:
                        if trout in self.trout:
                            self.trout.remove(trout)
                        self.events.append({"type": "eat", "position": (shark.x, shark.y), "energy": energy, "eater": "tiburon"})
                        break

    def _balance_populations(self):
        if len(self.plants) < cfg.POPULATION_LIMITS["plantas"]["min"]:
            deficit = cfg.POPULATION_LIMITS["plantas"]["min"] - len(self.plants)
            for _ in range(deficit):
                plant = Plant(0, 0)
                self._assign_id(plant)
                plant.set_random_position()
                self.plants.append(plant)

        elif len(self.plants) > cfg.POPULATION_LIMITS["plantas"]["max"]:
            excess = len(self.plants) - cfg.POPULATION_LIMITS["plantas"]["max"]
            self.plants = self.plants[:-excess] if excess > 0 else []

    # --------- UTILIDADES DE BÚSQUEDA ----------
    def get_nearby_entities(self, entity: Entity, radius: float, entity_list: List[Entity]) -> List[Entity]:
        nearby: List[Entity] = []
        for other in entity_list:
            if other == entity:
                continue
            dx = other.x - entity.x
            dy = other.y - entity.y
            d = math.hypot(dx, dy)
            if d <= radius:
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
        predators: List[Animal] = []
        if isinstance(entity, Fish):
            predators.extend(self.get_nearby_trout(entity, radius))
            predators.extend(self.get_nearby_sharks(entity, radius))
        elif isinstance(entity, Trout):
            predators.extend(self.get_nearby_sharks(entity, radius))
        return predators

    def form_trout_pack(self, leader: Trout, radius: float, max_size: int) -> List[Trout]:
        allies = self.get_nearby_trout(leader, radius)
        pack: List[Trout] = [leader]
        for t in allies:
            if len(pack) >= max_size:
                break
            pack.append(t)
        return pack

    def get_statistics(self) -> Dict[str, Any]:
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
            "season_progress": (self.time_system.day % cfg.DAYS_PER_SEASON) / cfg.DAYS_PER_SEASON,
            "is_night": self.time_system.is_night(),
            "light_factor": self.time_system.get_light_factor(),
        }

    def set_paused(self, paused: bool):
        self.paused = paused

    # ==============================
    #      SERIALIZACIÓN ECOSYSTEM
    # ==============================
    def to_dict(self) -> Dict[str, Any]:
        return {
            "paused": self.paused,
            "simulation_speed": self.simulation_speed,
            "turn_count": self.turn_count,
            "next_entity_id": self._next_entity_id,
            "time_system": self.time_system.to_dict(),
            "plants": [p.to_dict() for p in self.plants],
            "fish": [f.to_dict() for f in self.fish],
            "trout": [t.to_dict() for t in self.trout],
            "sharks": [s.to_dict() for s in self.sharks],
        }

    def load_from_dict(self, data: Dict[str, Any]):
        self.plants.clear()
        self.fish.clear()
        self.trout.clear()
        self.sharks.clear()
        self.events.clear()

        self.paused = bool(data.get("paused", False))
        self.simulation_speed = float(data.get("simulation_speed", 1.0))
        self.turn_count = int(data.get("turn_count", 0))
        self._next_entity_id = int(data.get("next_entity_id", 1))
        self.time_system = TimeSystem.from_dict(data.get("time_system", {}))

        id_map: Dict[int, Entity] = {}

        for pd in data.get("plants", []):
            p = Plant.from_dict(pd)
            id_map[p.eid] = p
            self.plants.append(p)

        for fd in data.get("fish", []):
            f = Fish.from_dict(fd)
            id_map[f.eid] = f
            self.fish.append(f)

        for td in data.get("trout", []):
            t = Trout.from_dict(td)
            id_map[t.eid] = t
            self.trout.append(t)

        for sd in data.get("sharks", []):
            s = Shark.from_dict(sd)
            id_map[s.eid] = s
            self.sharks.append(s)

        # reconstruir referencias target_entity
        for a in list(self.fish) + list(self.trout) + list(self.sharks):
            tid = getattr(a, "_pending_target_id", None)
            if isinstance(tid, int):
                a.target_entity = id_map.get(tid)
            a._pending_target_id = None
