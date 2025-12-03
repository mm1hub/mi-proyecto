"""
Lógica central del ecosistema.
Contiene todas las entidades y sus reglas de comportamiento.
Versión simplificada pero bien estructurada.
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
        
    def move_towards_target(self, speed: float):
        """Mueve la entidad hacia su objetivo."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        
        # Si está muy cerca, llegó
        if abs(dx) < 1 and abs(dy) < 1:
            self.x = self.target_x
            self.y = self.target_y
            self.update_position()
            return True
            
        # Movimiento interpolado
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            self.x += (dx / distance) * speed
            self.y += (dy / distance) * speed
            self.update_position()
            
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
    
    def __init__(self, x: float, y: float, width: int, height: int, name: str,
                 energy: float, max_energy: float, lifespan: int):
        super().__init__(x, y, width, height, name)
        
        self.energy = energy
        self.max_energy = max_energy
        self.lifespan = lifespan
        self.age = 0
        self.base_speed = random.uniform(0.5, 1.5)
        self.speed = self.base_speed
        self.base_consumption = 2.0
        self.consumption = self.base_consumption
        self.direction = 1  # 1 = derecha, -1 = izquierda
        
        # Estado de IA
        self.state = "idle"
        self.target_entity = None
        
    def update(self, delta_time: float, ecosystem: 'Ecosystem'):
        """Actualiza el estado del animal."""
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
        
    def is_dead(self) -> bool:
        """Verifica si el animal ha muerto."""
        return self.energy <= 0 or self.age >= self.lifespan
        
    @abstractmethod
    def decide_action(self, ecosystem: 'Ecosystem'):
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
    def reproduce(self) -> Optional['Animal']:
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
    """Pez herbívoro que come plantas."""
    
    def __init__(self, x: float, y: float, name: str = "Pejerrey"):
        super().__init__(x, y, 20, 20, name, energy=70, max_energy=100, lifespan=120)
        self.speed = random.uniform(1.0, 2.0)
        self.consumption = 1.0
        
    def decide_action(self, ecosystem: 'Ecosystem'):
        """Lógica de IA del pez."""
        # Buscar depredadores cercanos
        predators = ecosystem.get_nearby_predators(self, 150)
        if predators:
            # Huir del depredador más cercano
            predator = predators[0]
            dx = self.x - predator.x
            dy = self.y - predator.y
            
            # Normalizar y alejarse
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                flee_distance = 100
                self.target_x = self.x + (dx / distance) * flee_distance
                self.target_y = self.y + (dy / distance) * flee_distance
                self.state = "fleeing"
                return
                
        # Buscar plantas si tiene hambre
        if self.energy < self.max_energy * 0.3:
            plants = ecosystem.get_nearby_plants(self, 100)
            if plants:
                plant = plants[0]
                self.target_x = plant.x
                self.target_y = plant.y
                self.state = "eating"
                return
                
        # Movimiento aleatorio
        if random.random() < 0.05:
            self.target_x = self.x + random.randint(-50, 50)
            self.target_y = self.y + random.randint(-50, 50)
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
        return (self.energy > self.max_energy * 0.7 and 
                self.age > 3 and 
                random.random() < 0.1)
        
    def reproduce(self) -> Optional['Fish']:
        if not self.can_reproduce():
            return None
            
        # Coste de reproducción
        self.energy -= 30
        
        # Crear cría
        baby = Fish(self.x, self.y)
        baby.energy = 50
        return baby


class Trout(Animal):
    """Trucha que come peces."""
    
    def __init__(self, x: float, y: float, name: str = "Trucha"):
        super().__init__(x, y, 35, 35, name, energy=120, max_energy=180, lifespan=180)
        self.speed = random.uniform(0.75, 1.75)
        self.consumption = 1.5
        
    def decide_action(self, ecosystem: 'Ecosystem'):
        """Lógica de IA de la trucha."""
        # Huir de tiburones
        sharks = ecosystem.get_nearby_sharks(self, 150)
        if sharks:
            shark = sharks[0]
            dx = self.x - shark.x
            dy = self.y - shark.y
            
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                flee_distance = 120
                self.target_x = self.x + (dx / distance) * flee_distance
                self.target_y = self.y + (dy / distance) * flee_distance
                self.state = "fleeing"
                return
                
        # Cazar peces si tiene hambre
        if self.energy < self.max_energy * 0.4:
            fishes = ecosystem.get_nearby_fish(self, 200)
            if fishes:
                fish = fishes[0]
                self.target_x = fish.x
                self.target_y = fish.y
                self.state = "hunting"
                return
                
        # Movimiento aleatorio
        if random.random() < 0.03:
            self.target_x = self.x + random.randint(-80, 80)
            self.target_y = self.y + random.randint(-80, 80)
            self.state = "moving"
            
    def can_eat(self, other: Entity) -> bool:
        return isinstance(other, Fish)
        
    def eat(self, other: Entity) -> float:
        if not self.can_eat(other):
            return 0.0
            
        energy = min(35, other.energy * 0.5)
        self.energy = min(self.max_energy, self.energy + energy)
        self.state = "idle"
        return energy
        
    def can_reproduce(self) -> bool:
        return (self.energy > self.max_energy * 0.6 and 
                self.age > 6 and 
                random.random() < 0.08)
        
    def reproduce(self) -> Optional['Trout']:
        if not self.can_reproduce():
            return None
            
        self.energy -= 50
        baby = Trout(self.x, self.y)
        baby.energy = 100
        return baby


class Shark(Animal):
    """Tiburón que comer truchas."""
    
    def __init__(self, x: float, y: float, name: str = "Tiburón"):
        super().__init__(x, y, 45, 45, name, energy=200, max_energy=300, lifespan=30)
        self.speed = random.uniform(0.4, 1.2)
        self.consumption = 0.8
        
    def decide_action(self, ecosystem: 'Ecosystem'):
        """Lógica de IA del tiburón."""
        # Cazar truchas si tiene hambre
        if self.energy < self.max_energy * 0.5:
            trout = ecosystem.get_nearby_trout(self, 300)
            if trout:
                target = trout[0]
                self.target_x = target.x
                self.target_y = target.y
                self.state = "hunting"
                self.target_entity = target
                return
                
        # Movimiento de patrullaje
        if random.random() < 0.02:
            self.target_x = self.x + random.randint(-150, 150)
            self.target_y = self.y + random.randint(-150, 150)
            self.state = "patrolling"
            
    def can_eat(self, other: Entity) -> bool:
        return isinstance(other, Trout)
        
    def eat(self, other: Entity) -> float:
        if not self.can_eat(other):
            return 0.0
            
        energy = min(85, other.energy * 0.7)
        self.energy = min(self.max_energy, self.energy + energy)
        self.state = "idle"
        self.target_entity = None
        return energy
        
    def can_reproduce(self) -> bool:
        return (self.energy > self.max_energy * 0.7 and 
                self.age > 8 and 
                random.random() < 0.05)
        
    def reproduce(self) -> Optional['Shark']:
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
        dead_fish = []
        new_fish = []
        
        for fish in self.fish:
            if not fish.update(delta_time, self):
                dead_fish.append(fish)
            elif fish.can_reproduce():
                baby = fish.reproduce()
                if baby:
                    baby.set_random_position()
                    new_fish.append(baby)
                    self.events.append({
                        'type': 'birth',
                        'position': (fish.x, fish.y),
                        'species': 'pez'
                    })
                    
        # Truchas
        dead_trout = []
        new_trout = []
        
        for trout in self.trout:
            if not trout.update(delta_time, self):
                dead_trout.append(trout)
            elif trout.can_reproduce():
                baby = trout.reproduce()
                if baby:
                    baby.set_random_position()
                    new_trout.append(baby)
                    self.events.append({
                        'type': 'birth',
                        'position': (trout.x, trout.y),
                        'species': 'trucha'
                    })
                    
        # Tiburones
        dead_sharks = []
        new_sharks = []
        
        for shark in self.sharks:
            if not shark.update(delta_time, self):
                dead_sharks.append(shark)
            elif shark.can_reproduce():
                baby = shark.reproduce()
                if baby:
                    baby.set_random_position()
                    new_sharks.append(baby)
                    self.events.append({
                        'type': 'birth',
                        'position': (shark.x, shark.y),
                        'species': 'tiburon'
                    })
                    
        # Eliminar muertos
        for fish in dead_fish:
            if fish in self.fish:
                self.fish.remove(fish)
                self.events.append({
                    'type': 'death',
                    'position': (fish.x, fish.y)
                })
                
        for trout in dead_trout:
            if trout in self.trout:
                self.trout.remove(trout)
                self.events.append({
                    'type': 'death',
                    'position': (trout.x, trout.y)
                })
                
        for shark in dead_sharks:
            if shark in self.sharks:
                self.sharks.remove(shark)
                self.events.append({
                    'type': 'death',
                    'position': (shark.x, shark.y)
                })
                
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
                        self.plants.remove(plant)
                        self.events.append({
                            'type': 'eat',
                            'position': (fish.x, fish.y),
                            'energy': energy,
                            'eater': 'pez'
                        })
                        break
                        
        # Truchas comen peces
        for trout in self.trout:
            for fish in self.fish[:]:
                if trout.rect.colliderect(fish.rect):
                    energy = trout.eat(fish)
                    if energy > 0:
                        self.fish.remove(fish)
                        self.events.append({
                            'type': 'eat',
                            'position': (trout.x, trout.y),
                            'energy': energy,
                            'eater': 'trucha'
                        })
                        break
                        
        # Tiburones comen truchas
        for shark in self.sharks:
            for trout in self.trout[:]:
                if shark.rect.colliderect(trout.rect):
                    energy = shark.eat(trout)
                    if energy > 0:
                        self.trout.remove(trout)
                        self.events.append({
                            'type': 'eat',
                            'position': (shark.x, shark.y),
                            'energy': energy,
                            'eater': 'tiburon'
                        })
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
            
    def get_nearby_entities(self, entity: Entity, radius: float, entity_list: List[Entity]) -> List[Entity]:
        """Obtiene entidades cercanas a una posición."""
        nearby = []
        for other in entity_list:
            if other == entity:
                continue
                
            dx = other.x - entity.x
            dy = other.y - entity.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance <= radius:
                nearby.append(other)
                
        # Ordenar por distancia
        nearby.sort(key=lambda e: math.sqrt((e.x - entity.x)**2 + (e.y - entity.y)**2))
        return nearby
        
    def get_nearby_plants(self, entity: Entity, radius: float) -> List[Plant]:
        return self.get_nearby_entities(entity, radius, self.plants)
        
    def get_nearby_fish(self, entity: Entity, radius: float) -> List[Fish]:
        return self.get_nearby_entities(entity, radius, self.fish)
        
    def get_nearby_trout(self, entity: Entity, radius: float) -> List[Trout]:
        return self.get_nearby_entities(entity, radius, self.trout)
        
    def get_nearby_sharks(self, entity: Entity, radius: float) -> List[Shark]:
        return self.get_nearby_entities(entity, radius, self.sharks)
        
    def get_nearby_predators(self, entity: Entity, radius: float) -> List[Animal]:
        """Obtiene depredadores cercanos."""
        predators = []
        if isinstance(entity, Fish):
            predators.extend(self.get_nearby_trout(entity, radius))
            predators.extend(self.get_nearby_sharks(entity, radius))
        elif isinstance(entity, Trout):
            predators.extend(self.get_nearby_sharks(entity, radius))
        return predators
        
    def get_statistics(self) -> Dict[str, Any]:
        """Obtiene estadísticas actuales."""
        return {
            'plants': len(self.plants),
            'fish': len(self.fish),
            'trout': len(self.trout),
            'sharks': len(self.sharks),
            'turn': self.turn_count,
            'season': self.time_system.get_season(),
            'day': self.time_system.day,
            'time_of_day': self.time_system.get_time_of_day(),
            'day_progress': self.time_system.day_progress,
            'season_progress': (self.time_system.day % cfg.DAYS_PER_SEASON) / cfg.DAYS_PER_SEASON,
            'is_night': self.time_system.is_night(),
            'light_factor': self.time_system.get_light_factor()
        }
        
    def set_paused(self, paused: bool):
        """Pausa o reanuda la simulación."""
        self.paused = paused