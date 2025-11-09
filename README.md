Simulador de Ecosistema (Pygame)
================================

Descripción
- Simulación simple con peces, truchas, tiburones y algas.
- Programación orientada a objetos: cada entidad define su lógica y movimiento.
- Ventana fija a 1024x768; las entidades no salen de los bordes.

Requisitos
- Python 3.10+
- pygame (`pip install pygame`)

Ejecución
- `python main.py`

Controles
- Cerrar ventana para salir.

Arquitectura
- `logic.py`: Modelo y reglas del ecosistema (POO)
  - Clases: `Animal` (abstracta), `Pez`, `Trucha`, `Tiburon`, `Planta`, `Ecosistema`.
  - Movimiento suave por frame y decisiones por turnos.
  - Limitación de posición al área visible.
- `view.py`: Vista y renderizado con Pygame
  - `Vista` inicializa `pygame`, crea la ventana `1024x768` y dibuja entidades/UI.
  - Usa sprites de `assets/` si existen; si no, dibuja formas básicas.
- `main.py`: Bucle principal
  - Inicializa `Ecosistema` y `Vista`, ejecuta turnos de IA y render.
