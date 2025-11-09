Simulador de Ecosistema (Pygame)
================================

Descripcion
- Simulacion con peces, truchas, tiburones y algas.
- Peces comen algas; truchas comen peces; tiburones comen truchas.
- POO: cada entidad define su logica y movimiento.
- Ventana fija a 1024x768; las entidades respetan los bordes.

Requisitos
- Python 3.10+
- pygame (`pip install pygame`)

Ejecucion
- `python main.py`

Controles
- Cerrar ventana para salir.

Arquitectura
- `logic.py`: Modelo y reglas del ecosistema (POO)
  - Clases: `Animal` (abstracta), `Pez`, `Trucha`, `Tiburon`, `Planta`, `Ecosistema`.
  - Movimiento suave por frame y decisiones por turnos.
  - Posicion limitada al area visible.
- `view.py`: Vista y renderizado con Pygame
  - `Vista` inicializa `pygame`, crea la ventana `1024x768` y dibuja entidades/UI.
  - Usa sprites de `assets/` si existen; si no, dibuja formas basicas.
- `main.py`: Bucle principal
  - Inicializa `Ecosistema` y `Vista`, ejecuta turnos de IA y render.

Mejoras recientes (IA y rendimiento)
- Peces: comportamiento de cardumen (cohesion + alineacion) para nadar en grupo de forma natural.
- Depredadores: persecucion mas inteligente con prediccion simple de la trayectoria de la presa.
- Huida de peces mas realista (evade vectorial con leve ruido).
- Vecindad acelerada por particion espacial (grid) para reducir O(n^2) en separacion/boids por frame.
- Mantiene equilibrio entre realismo y eficiencia sin dependencias extra.

Controles de la UI
- Boton `Comenzar`: inicia la simulacion con los valores de la barra superior.
- Boton `Pausar/Reanudar`: pausa o reanuda el avance.
- Boton `Detener`: reinicia poblaciones y deja la simulacion detenida.

Configuracion previa
- Antes de iniciar, puedes ajustar las cantidades de Algas, Peces, Truchas y Tiburones con los botones - y + en la barra superior.
- Si no cambias nada, se usan los valores predeterminados.

Assets
- Coloca las imagenes en la carpeta `assets/` junto al codigo.

