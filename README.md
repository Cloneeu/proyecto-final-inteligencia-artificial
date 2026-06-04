# Trazado automático de circuitos impresos

Herramienta web para diseñar y visualizar rutas de conexión entre componentes
electrónicos sobre una placa de circuito impreso. El sistema coloca componentes
en una cuadrícula, define conexiones entre ellos y calcula trayectorias óptimas
evitando obstáculos y cruces, usando tres algoritmos de búsqueda de caminos.

La interfaz está inspirada en software EDA profesional (KiCad, EasyEDA) e incluye
modo claro y oscuro, zoom, desplazamiento, estadísticas y exportación a JSON,
CSV, PNG y PDF.

---

## ejecucion 

**Windows**

```bat
cd pcb_router
iniciar.bat
```

depues abrir "http://localhost:8000"



## Cómo se usa

1. **Configura la placa** en el panel derecho (filas, columnas, tamaño de celda)
   y pulsa "Aplicar placa".
2. **Agrega componentes** de dos formas:
   - Rellenando el formulario del panel derecho y pulsando "Agregar componente".
   - Eligiendo la herramienta de componente (icono cuadrado en la barra
     izquierda) y haciendo clic sobre la cuadrícula.
   - Importando un archivo JSON o CSV con el botón "Importar".
3. **Define conexiones** entre componentes con los selectores de origen/destino,
   o con la herramienta de conexión (haz clic en el componente origen y luego en
   el destino).
4. **Elige el algoritmo** (A*, Dijkstra o BFS) y pulsa **"Trazar rutas"**.
   Verás la animación de exploración y luego las pistas finales.
5. **Exporta** el resultado a JSON, PNG o PDF desde la barra superior.

Atajos del lienzo: rueda del ratón para zoom, **Shift + arrastrar** para mover
la vista, y el botón de ajustar para centrar la placa.

---

## Algoritmos de trazado

Los tres trabajan sobre la misma cuadrícula con movimiento ortogonal (arriba,
abajo, izquierda, derecha), que es lo habitual en pistas de PCB. Como el coste
por celda es uniforme, los tres encuentran el **mismo camino más corto**; lo que
cambia es cuántas celdas exploran para llegar a él.

- **A\*** — Usa la distancia Manhattan como heurística para guiarse hacia el
  destino. Es el más eficiente: explora menos celdas.
- **Dijkstra** — Explora por coste real acumulado, sin heurística. Encuentra el
  óptimo pero explora más celdas que A*.
- **BFS** — Explora por capas con una cola simple. Útil como referencia porque
  con coste uniforme también garantiza el camino más corto.

Poder elegir entre los tres permite comparar el número de nodos explorados y el
tiempo de cálculo en el panel de estadísticas.

### Detección de colisiones y cruces

- Cada componente marca su área como un obstaculo, las pistas no pasan por
  encima.
- Cada pista trazada se marca en la cuadrícula. Si "Evitar cruces de pistas"
  está activo, las siguientes rutas **no cruzan** las anteriores.
- Si una conexión no tiene camino posible, se reporta como conexion fallida y aparece
  un aviso pero no detiene el trazado del resto.



## Limitaciones conocidas

- El estado del proyecto se mantiene **en memoria** del servidor. Al reiniciar
  el servidor se pierde, por eso conviene exportar a JSON para guardar.
- El trazado usa una sola capa. No modela vías ni múltiples capas de cobre.
- El movimiento es ortogonal; no traza pistas en diagonal a 45°.

Estas decisiones mantienen el proyecto claro y enfocado; ampliarlo a varias
capas o a guardado en disco es un siguiente paso natural.
