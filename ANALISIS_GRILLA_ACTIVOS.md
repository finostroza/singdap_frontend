# Análisis Funcional de la Grilla de Activos

## 1. Construcción Visual
La grilla es un componente `QTableWidget` estándar de Qt, pero con un estilo personalizado minimalista:
- **Columnas Fijas:** Tiene 9 columnas definidas (ID, Nombre, Tipo, Estado, Subsecretaría, División, Confidencialidad, EIPD y Acciones).
- **Estilo:** Muestra filas alternadas (colores cebra), sin líneas de cuadrícula visibles (`setShowGrid(False)`), y selección de fila completa.
- **Cabecera:** La columna de "Acciones" (última) tiene ancho fijo, mientras que "Nombre" y "Subsecretaría" se estiran elásticamente para ocupar el espacio disponible.

## 2. Flujo de Obtención de Datos (Carga Asíncrona)
La grilla **NO** carga datos directamente en el hilo principal de la aplicación.
1. **Disparador:** Al abrir la vista, o al usar filtros/buscadores, se activa el método `_reload_all()`.
2. **Estado de Carga:** Inmediatamente se muestra un "Overlay" (spinner) que bloquea la interacción.
3. **Hilo Separado (ApiWorker):**
   - Se lanzan peticiones HTTP paralelas para obtener los Activos (según filtros) y los Indicadores (tarjetas superiores) al mismo tiempo en un segundo plano.
   - Recopila Estado (search, combos) -> Petición API -> Devuelve JSON.
4. **Renderizado:**
   - Una vez que los datos llegan (evento `finished`), el hilo principal retoma el control.
   - Limpia la tabla y la reconstruye fila por fila.
   - Oculta el spinner de carga.

## 3. Lógica de Filtrado y Paginación
Toda la lógica de filtrado ocurre en el **Servidor (Backend)**, la grilla es solo un visualizador ("receptáculo"):
- **Filtros:** Cuando cambias una subsecretaría, tipo o escribes en el buscador, no se filtra la lista visualmente en local. En su lugar, se reinicia la página a 1 y se lanza una nueva petición al servidor con esos parámetros (`?search=...&subsecretaria_id=...`).
- **Paginación:** Mantiene el estado de `current_page` y `total_pages`. Los botones "Anterior" y "Siguiente" simplemente incrementan/decrementan este contador y vuelven a ejecutar la recarga completa (`_reload_all`).

## 4. Acciones y Eventos
La columna "Acciones" no contiene texto, sino "Widgets" incrustados (Botones Editar y Eliminar):
- Se generan dinámicamente por cada fila.
- **Editar:** Abre el diálogo modal `ActivoDialog` y, si este se cierra con éxito ("Guardar"), recarga toda la grilla automáticamente para mostrar los cambios.
- **Eliminar:** Muestra una alerta de confirmación. Si se acepta, envía la orden de borrado al servidor y recarga la grilla.
- **Registro (Logs):** Cada acción importante (búsqueda, filtrado, eliminación) inyecta silenciosamente un evento en el sistema de logs (`LoggerService`) en segundo plano.

## Resumen
Es una **Grilla Pasiva y Reactiva**: No procesa datos ni cálculos pesados. Su única responsabilidad es pedir datos al servidor según la configuración actual de filtros/página, esperar pacientemente (con spinner) a que lleguen, y dibujarlos limpiamente.
