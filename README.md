# Simulador de Ecosistema "Benyi" 🐟🌿

¡Hola! Este es un simulador de vida acuática desarrollado en Python con Pygame. El proyecto recrea un pequeño ecosistema donde distintas especies interactúan, comen, se reproducen y sobreviven en base a un sistema de estaciones y ciclos de día/noche.

Lo más interesante de esta versión 2.0 es que **hemos reescrito la arquitectura** para que sea profesional, modular y escalable. Nada de código espagueti.

## ¿Qué puedes hacer aquí?

La simulación no es solo "peces nadando". Hay reglas biológicas y de entorno:

* **Cadena Alimenticia:** Las algas crecen con el sol → Los peces comen algas → Las truchas cazan peces → Los tiburones dominan la cima.
* **Comportamiento Animal:** Verás que los peces forman cardúmenes (nadan juntos), las truchas cazan en grupo y los tiburones patrullan buscando rastro.
* **Ciclo de Vida:** Si no comen, mueren. Si comen suficiente y tienen la edad adecuada, se reproducen.
* **Entorno Vivo:** Hay ciclos de día y noche, y pasan las 4 estaciones (Primavera, Verano, Otoño, Invierno). Esto afecta qué tan rápido se mueven o cuánta energía gastan.

## 🏛️ Sobre la Arquitectura (Novedad)

Para esta versión, me enfoqué en separar las responsabilidades correctamente. Si revisas el código, verás una **Arquitectura en Capas** estricta:

1.  **Vista (`game_view.py`):** Solo se encarga de dibujar y detectar clics. No toma decisiones, solo muestra lo que le dicen.
2.  **Controlador (`main.py`):** Es el "jefe de orquesta". Conecta la vista con la lógica y maneja los eventos.
3.  **Lógica (`game_logic.py`):** Aquí viven las reglas del juego (matemáticas, colisiones, IA). No sabe nada de la interfaz gráfica.
4.  **Persistencia (`save_system.py`):** Se encarga exclusivamente de guardar y cargar los archivos JSON.

> **Nota:** Gracias a esto, la interfaz nunca toca directamente la base de datos de guardado, evitando errores comunes y haciendo el código mucho más limpio.

## 🎮 Controles

El simulador se controla desde el panel lateral derecho.

### Botones Principales
* **COMENZAR:** Arranca la simulación (necesitas crear o seleccionar una partida primero).
* **PAUSAR / REANUDAR:** Congela el tiempo para que puedas ver detalles. (Atajo: `ESPACIO`).
* **DETENER:** Vuelve al modo de edición.
* **GUARDAR:** Hace un guardado manual rápido.

### Gestor de Partidas
Puedes tener varias partidas guardadas ("slots").
* **Crear:** Escribe un nombre y dale a "Crear".
* **Cargar:** Selecciona una de la lista y carga sus datos.
* **Editar:** Tienes botoncitos para renombrar (`r`) o borrar (`x`) partidas.

### 💾 Autoguardado (Nuevo)
Para no perder progreso, implementé un sistema automático:
* Activa el switch **AUTO** en el panel.
* Elige cada cuántos días quieres que guarde (por defecto cada 30 días de simulación).
* El sistema hace copias de seguridad (backups) automáticas antes de sobrescribir nada importante.

## 🚀 Cómo ejecutarlo

Es muy sencillo. Solo necesitas Python (3.10 o superior) y la librería `pygame`.

1.  Instala la librería:
    ```bash
    pip install pygame
    ```

2.  Corre el archivo principal:
    ```bash
    python main.py
    ```

## Estructura de Archivos

Si quieres curiosear el código, aquí está lo importante:

* `main.py`: El punto de entrada y controlador.
* `game_logic.py`: Donde ocurre la magia de la simulación.
* `game_view.py`: Todo lo relacionado con gráficos y UI.
* `save_system.py`: El manejo de archivos JSON.
* `config.py`: Si quieres cambiar colores o velocidades, toca aquí.
* `assets/`: Carpeta con las imágenes y sonidos.

---
*Hecho con ❤️ y Python.*