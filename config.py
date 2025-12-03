"""
Configuración central del juego.
Única fuente de verdad para constantes y colores.
"""

from pygame import Color

# ============================================================================
# DIMENSIONES Y TIEMPO
# ============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
PANEL_WIDTH = 280
GAME_AREA_WIDTH = SCREEN_WIDTH - PANEL_WIDTH

# Tiempo de simulación
TURN_DURATION_MS = 1000  # 1 segundo por turno de IA

# ============================================================================
# CICLO DÍA/NOCHE Y ESTACIONES
# ============================================================================
DAY_CYCLE_TURNS = 32
DAWN_FRACTION = 0.18
DUSK_FRACTION = 0.68
DAYS_PER_SEASON = 6
SEASONS_ORDER = ("Primavera", "Verano", "Otoño", "Invierno")

# ============================================================================
# POBLACIÓN POR DEFECTO AND LÍMITES
# ============================================================================
DEFAULT_POPULATION = {
    "plantas": 25,
    "peces": 15,
    "truchas": 5,
    "tiburones": 2,
}

POPULATION_LIMITS = {
    "plantas": {"min": 0, "max": 100},
    "peces": {"min": 0, "max": 50},
    "truchas": {"min": 0, "max": 30},
    "tiburones": {"min": 0, "max": 15},
}

# ============================================================================
# COLORES
# ============================================================================
# Colores base
WHITE = Color(255, 255, 255)
BLACK = Color(0, 0, 0)
BLUE = Color(0, 0, 255)
GREEN = Color(0, 255, 0)
BROWN = Color(139, 69, 19)
GRAY = Color(169, 169, 169)

# Colores del ambiente
WATER_LIGHT = Color(173, 216, 230)
WATER_DARK = Color(0, 105, 148)
UI_BLACK = Color(20, 20, 20)

# Colores de UI
PANEL_BG = Color(33, 37, 41, 230)
TEXT_TITLE = Color(248, 249, 250)
TEXT_NORMAL = Color(206, 212, 218)
BAR_BG = Color(73, 80, 87)
BAR_PROGRESS = Color(0, 123, 255)
SEPARATOR = Color(108, 117, 125)

# Colores de botones
BTN_TEXT = Color(255, 255, 255)
BTN_START = Color(40, 167, 69)
BTN_STOP = Color(220, 53, 69)
BTN_PAUSE = Color(255, 193, 7)
BTN_RESUME = Color(23, 162, 184)
BTN_PLUS = Color(40, 167, 69)
BTN_MINUS = Color(220, 53, 69)

# Colores de efectos
EAT_COLOR = Color(144, 238, 144)
BIRTH_COLOR = Color(255, 182, 193)
DEATH_COLOR = Color(160, 160, 160)
BUBBLE_COLOR = Color(200, 225, 255)

# ============================================================================
# CONFIGURACIÓN DE ESTACIONES
# ============================================================================
SEASONS_CONFIG = {
    "Primavera": {
        "color": Color(138, 227, 185),
        "description": "Brotes templados y corrientes suaves.",
        "objective": "Mantén al menos 25 algas vivas antes del verano.",
        "modifiers": {
            "movement": 1.05,
            "energy_consumption": 0.92,
            "plant_regeneration": 1.2,
            "fertility": {"peces": 1.3, "truchas": 1.15, "tiburones": 1.05},
        },
    },
    "Verano": {
        "color": Color(255, 214, 161),
        "description": "Calor intenso y migraciones veloces.",
        "objective": "Supera el verano sin perder más de 3 peces.",
        "modifiers": {
            "movement": 1.08,
            "energy_consumption": 1.05,
            "plant_regeneration": 1.05,
            "fertility": {"peces": 1.05, "truchas": 1.0, "tiburones": 1.15},
        },
    },
    "Otoño": {
        "color": Color(255, 183, 120),
        "description": "Corrientes cargadas de hojas, ritmo pausado.",
        "objective": "Mantén la cadena alimenticia equilibrada en otoño.",
        "modifiers": {
            "movement": 0.95,
            "energy_consumption": 0.98,
            "plant_regeneration": 0.85,
            "fertility": {"peces": 0.9, "truchas": 0.95, "tiburones": 1.0},
        },
    },
    "Invierno": {
        "color": Color(173, 209, 255),
        "description": "Aguas frías y escasez de alimento.",
        "objective": "Sobrevive al invierno manteniendo 3 tiburones activos.",
        "modifiers": {
            "movement": 0.82,
            "energy_consumption": 1.2,
            "plant_regeneration": 0.55,
            "fertility": {"peces": 0.7, "truchas": 0.8, "tiburones": 0.9},
        },
    },
}

# ============================================================================
# COMPORTAMIENTO DE ESPECIES (NUEVO)
# ============================================================================

# Velocidades base (parametrizadas)
FISH_BASE_SPEED_MIN = 1.0
FISH_BASE_SPEED_MAX = 2.0

TROUT_BASE_SPEED_MIN = 0.9
TROUT_BASE_SPEED_MAX = 1.9

SHARK_BASE_SPEED_MIN = 0.9
SHARK_BASE_SPEED_MAX = 1.3

# Cardúmenes de peces (boids simplificado)
FISH_SCHOOL_RADIUS = 140          # Radio para considerar vecinos de cardumen
FISH_SCHOOL_MIN_NEIGHBORS = 2     # Mínimo de vecinos para comportarse en cardumen
FISH_SEPARATION_DISTANCE = 30     # Distancia mínima antes de separarse

# Truchas cazando en grupo
TROUT_PACK_RADIUS = 220           # Radio para buscar compañeras de caza
TROUT_MAX_PACK_SIZE = 3           # Tamaño máximo del grupo de ataque
TROUT_MIN_ALLIES_FOR_PACK = 1     # Nº mínimo de compañeras para formar grupo

# Truchas escapando de tiburones
TROUT_ESCAPE_RADAR = 190              # Radio para detectar tiburones peligrosos
TROUT_ESCAPE_SPEED_MULTIPLIER = 1.6   # Multiplicador de velocidad al huir

# Tiburones
SHARK_HUNGER_THRESHOLD = 0.65     # Cuando pasan esta proporción se vuelven más agresivos
SHARK_HUNT_RADIUS_RELAXED = 260   # Radio de caza normal
SHARK_HUNT_RADIUS_HUNGRY = 400    # Radio de caza cuando están muy hambrientos
SHARK_TARGET_PERSISTENCE = 480    # Distancia máxima para seguir persiguiendo a la misma trucha
