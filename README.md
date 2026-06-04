# Trazado automático de circuitos impresos

Herramienta web para diseñar y visualizar rutas de conexión entre componentes
electrónicos sobre una placa de circuito impreso. El sistema coloca componentes
en una cuadrícula, define conexiones entre ellos y calcula trayectorias óptimas
evitando obstáculos y cruces, usando tres algoritmos de búsqueda de caminos.

La interfaz está inspirada en software profesional KiCad e incluye
modo claro y oscuro, zoom, desplazamiento, estadísticas y exportación a JSON,
CSV, PNG y PDF.

---

## Equipo BETA:

- Alexandro Vega Ramírez
- Alondra Jacqueline González Corona
- Mauricio Betancourt Chabolla
- Yoed Gutierrez Velarde

---

## ejecucion 

Se debe estar adentro de la carpeta del proyecto en una terminal, y ejecutar:

**Windows**

```bat
.\iniciar.bat
```

**Linux o Mac**

```bat
./iniciar.sh
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
3. **Define conexiones entre patitas**. Cada componente muestra sus patitas
   (terminales) como puntos en el borde, según su tipo: resistencia/capacitor/
   diodo/LED = 2, transistor = 3, y microcontrolador/integrado/conector usan el
   campo "N° de patitas" del formulario. Conéctalas con la herramienta de conexión
   (clic en la patita de origen y luego en la de destino) o con los selectores de
   origen/destino y patita del panel derecho.
4. **Elige el algoritmo** (A*, Dijkstra o BFS), activa **"Permitir 45°"** si
   quieres pistas diagonales, y pulsa **"Trazar rutas"**. Verás la animación de
   exploración y luego las pistas finales.
5. **Exporta** el resultado a JSON, PNG o PDF desde la barra superior. El PNG y el
   PDF reflejan la vista actual: símbolos electrónicos en esquemático, o placa real
   (verde, cobre y pads) si tienes activado "Ver PCB".
6. Pulsa **"Ver PCB"** para alternar el lienzo a una vista de placa real (verde,
   pistas de cobre y pads). Vuelve a pulsarlo para regresar al esquemático.
7. Pulsa **"Borrar todo"** para limpiar componentes, conexiones y rutas (la placa
   conserva su tamaño). Es reversible con "Deshacer".

Cada componente se dibuja con su **símbolo electrónico** según su tipo
(resistencia, capacitor, microcontrolador, LED, diodo, transistor, conector,
integrado), así que el esquemático se entiende de un vistazo.

Atajos del lienzo: rueda del ratón para zoom, **Shift + arrastrar** para mover
la vista, y el botón de ajustar para centrar la placa.

---

## Algoritmos de trazado

Los tres trabajan sobre la misma cuadrícula. Por defecto el movimiento es
ortogonal (arriba, abajo, izquierda, derecha), que es lo habitual en pistas de
PCB. Como el coste por celda es uniforme, los tres encuentran el **mismo camino
más corto**; lo que cambia es cuántas celdas exploran para llegar a él.

Si activas **"Permitir 45°"**, además se habilitan los movimientos diagonales
(coste √2). En ese caso A* usa la heurística octágono (octile) para seguir siendo
óptimo y Dijkstra pondera cada diagonal por su coste real; BFS sigue contando
cada paso por igual, por lo que puede dar un camino algo más largo.

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
- El trazado usa una sola capa. No modela vías ni múltiples capas de cobre, lamentablemente.
- El movimiento es ortogonal por defecto; las diagonales a 45° son opcionales
  (casilla "Permitir 45°").
