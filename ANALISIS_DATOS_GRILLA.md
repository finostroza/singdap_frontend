# Análisis de Fuentes de Datos: Grilla, Filtros y KPIs

## 1. Columnas de la Grilla (El contenido)
Las filas y columnas que ves en la tabla **NO** se construyen a partir de archivos caché locales ni de cruces de información en el frontend.
- **Fuente:** Vienen listas y "cocinadas" desde el servidor a través del endpoint principal `/activos/catalogos`.
- **Mecanismo:** Cuando la grilla se recarga, el servidor entrega un paquete JSON con los datos ya resueltos. Por ejemplo, en lugar de enviar solo el ID `5`, envía el texto "S. Evaluación Social". La aplicación solo se encarga de pintar ese texto en la celda correspondiente.
- **Validación:** La grilla muestra estrictamente lo que el servidor le entrega.

## 2. Filtros y Buscador (Desplegables y Caja de Texto)
Los menús desplegables (Comboboxes) de la barra superior:
- **Poblado Inicial:** Al abrir la ventana, la aplicación hace llamadas inmediatas a la API para buscar las listas de opciones:
  - `/setup/subsecretarias`
  - `/catalogos/tipo-activo`
  - `/catalogos/estado-evaluacion`
- **Funcionamiento:** Estas listas se cargan **en vivo** desde la API cada vez que entras a la vista (no usan el archivo de caché local que implementamos para el formulario de edición, lo cual garantiza que los filtros estén siempre al día).
- **Interacción:** Al seleccionar una opción, se envía el ID seleccionado como parámetro de consulta al servidor para que este devuelva la tabla filtrada.

## 3. Tarjetas Superiores (Indicadores KPI)
Los números grandes de la parte superior (Total Activos, Con datos sensibles, etc.):
- **Fuente:** Se obtienen de una llamada API exclusiva: `/activos/indicadores`.
- **Sincronización:** Esta llamada se ejecuta **en paralelo** con la carga de la grilla. Es decir, cada vez que filtras o cambias de página, se aprovecha el viaje al servidor para actualizar estos números y asegurar que coincidan con la realidad actual de la base de datos.

## Resumen Técnico Simplificado
| Componente | Fuente de Datos | ¿Usa Caché Local? |
| :--- | :--- | :--- |
| **Texto en Columnas** | Respuesta directa API `/activos/catalogos` | **No**. El servidor entrega textos listos. |
| **Opciones Filtros** | APIs independientes (`/setup/...`, `/catalogos/...`) | **No**. Se piden en vivo al iniciar la vista. |
| **Números KPIs** | API dedicada `/activos/indicadores` | **No**. Se calculan en tiempo real. |

**Nota:** A diferencia del formulario "Editar Activo" (que sí usa caché local para sus 10+ catálogos), la Vista de Grilla prioriza datos **en vivo** para asegurar que el inventario mostrado sea 100% exacto respecto al servidor.
