"""
Configuración central del juego.
Única fuente de verdad para constantes y colores.
DISEÑO ACTUALIZADO: TEMA MINIMALISTA 'DEEP OCEAN'
"""

from pygame import Color

# ============================================================================
# DIMENSIONES Y TIEMPO
# ============================================================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 768
FPS = 60
PANEL_WIDTH = 300  
GAME_AREA_WIDTH = SCREEN_WIDTH - PANEL_WIDTH

TURN_DURATION_MS = 1000
DAY_CYCLE_TURNS = 32
DAWN_FRACTION = 0.18
DUSK_FRACTION = 0.68
DAYS_PER_SEASON = 6
SEASONS_ORDER = ("Primavera", "Verano", "Otoño", "Invierno")

# ============================================================================
# POBLACIÓN POR DEFECTO Y LÍMITES
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
# PALETA DE COLORES (MODERNA / FLAT)
# ============================================================================

# --- UI General (Dark Theme) ---
UI_BG = Color("#1e2124")        # Fondo principal del panel (Gris muy oscuro)
UI_CARD_BG = Color("#282b30")   # Fondo de tarjetas/secciones (Gris medio)
UI_BORDER = Color("#36393e")    # Bordes sutiles

# --- Textos ---
TEXT_MAIN = Color("#ffffff")    # Blanco puro para lectura importante
TEXT_SEC = Color("#b9bbbe")     # Gris claro para etiquetas
TEXT_DIM = Color("#72767d")     # Gris oscuro para placeholders o info menos relevante
TEXT_ACCENT = Color("#7289da")  # Azul discord-like para títulos destacados

# --- Botones y Acciones ---
BTN_PRIMARY = Color("#5865f2")  # Azul vibrante (Acción principal: Start/Crear)
BTN_DANGER = Color("#ed4245")   # Rojo suave (Stop/Borrar)
BTN_WARNING = Color("#fee75c")  # Amarillo (Pausa)
BTN_SUCCESS = Color("#3ba55c")  # Verde (Guardar/Confirmar)
BTN_NEUTRAL = Color("#4f545c")  # Gris botón inactivo o secundario

# --- Barras de Progreso ---
BAR_BG = Color("#202225")
BAR_FILL = Color("#3ba55c")     # Verde genérico
BAR_SEASON = Color("#5865f2")   # Azul estación

# --- Entidades y Simulación ---
WHITE = Color(255, 255, 255)
BLACK = Color(0, 0, 0)

# Colores del ambiente (Renderizado)
WATER_LIGHT = Color(173, 216, 230)
WATER_DARK = Color(0, 105, 148)
UI_BLACK = Color(20, 20, 20)

# Colores de UI Legacy
PANEL_BG = UI_BG
TEXT_TITLE = TEXT_ACCENT
TEXT_NORMAL = TEXT_SEC
SEPARATOR = UI_BORDER

BTN_TEXT = TEXT_MAIN
BTN_START = BTN_PRIMARY
BTN_STOP = BTN_DANGER
BTN_PAUSE = BTN_WARNING
BTN_RESUME = BTN_PRIMARY
BTN_PLUS = BTN_NEUTRAL
BTN_MINUS = BTN_NEUTRAL

# Colores de Entidades (Barras estadísticas)
COLOR_PLANT = Color("#3ba55c")   # Verde
COLOR_FISH = Color("#00b0f4")    # Cyan
COLOR_TROUT = Color("#e67e22")   # Naranja
COLOR_SHARK = Color("#95a5a6")   # Gris tiburón

# Efectos
EAT_COLOR = Color(144, 238, 144)
BIRTH_COLOR = Color(255, 182, 193)
DEATH_COLOR = Color(160, 160, 160)
BUBBLE_COLOR = Color(200, 225, 255)

# ============================================================================
# CONFIGURACIÓN DE ESTACIONES
# ============================================================================
SEASONS_CONFIG = {
    "Primavera": {
        "color": Color("#3ba55c"), # Verde
        "description": "Brotes templados.",
        "modifiers": {"movement": 1.05, "energy_consumption": 0.92},
    },
    "Verano": {
        "color": Color("#f1c40f"), # Amarillo sol
        "description": "Calor intenso.",
        "modifiers": {"movement": 1.08, "energy_consumption": 1.05},
    },
    "Otoño": {
        "color": Color("#e67e22"), # Naranja hoja
        "description": "Corrientes de hojas.",
        "modifiers": {"movement": 0.95, "energy_consumption": 0.98},
    },
    "Invierno": {
        "color": Color("#3498db"), # Azul hielo
        "description": "Aguas frías.",
        "modifiers": {"movement": 0.82, "energy_consumption": 1.2},
    },
}

# Configuración de comportamiento de entidades
FISH_BASE_SPEED_MIN = 1.0
FISH_BASE_SPEED_MAX = 2.0
TROUT_BASE_SPEED_MIN = 0.9
TROUT_BASE_SPEED_MAX = 1.9
SHARK_BASE_SPEED_MIN = 0.9
SHARK_BASE_SPEED_MAX = 1.3
FISH_SCHOOL_RADIUS = 140
FISH_SCHOOL_MIN_NEIGHBORS = 2
FISH_SEPARATION_DISTANCE = 30
TROUT_PACK_RADIUS = 220
TROUT_MAX_PACK_SIZE = 3
TROUT_MIN_ALLIES_FOR_PACK = 1
TROUT_ESCAPE_RADAR = 190
TROUT_ESCAPE_SPEED_MULTIPLIER = 1.6
SHARK_HUNGER_THRESHOLD = 0.65
SHARK_HUNT_RADIUS_RELAXED = 260
SHARK_HUNT_RADIUS_HUNGRY = 400
SHARK_TARGET_PERSISTENCE = 480