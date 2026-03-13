from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout,
    QGridLayout, QScrollArea, QGraphicsDropShadowEffect,
    QPushButton, QSizePolicy, QSplitter, QToolTip
)
from PySide6.QtCore import Qt, QTimer, Slot, QRectF, QMargins
from PySide6.QtGui import QColor, QPainter, QFont, QPen
from PySide6.QtCharts import QChart, QChartView, QPieSeries

from src.viewmodels.dashboard_viewmodel import DashboardViewModel
from src.components.loading_overlay import LoadingOverlay


class TreeMapWidget(QWidget):
    """Widget de Tree Map optimizado para visualizar consultas por institución."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []  
        self.rects = [] 
        self.draw_rect = QRectF() # Inicializar para evitar AttributeError
        self.colors = [
            "#008cff", "#e66c37", "#242d8c", "#4c3273", "#1b3d36", 
            "#32a8a4", "#ff52a2", "#e84a5f", "#45b058", "#82589f"
        ]
        self.setMinimumHeight(150) # Reducido para permitir escalado en ventanas pequeñas
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True) # Habilitar para Tooltips dinámicos
        
        # Tooltip personalizado (Moderno)
        self.custom_tooltip = QLabel(self)
        self.custom_tooltip.setVisible(False)
        self.custom_tooltip.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.95);
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
            }
        """)
        self.custom_tooltip.setAttribute(Qt.WA_TransparentForMouseEvents)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.custom_tooltip.setGraphicsEffect(shadow)

    def setData(self, data):
        processed = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    # Soporte para campos antiguos (institucion/cantidad) y nuevos (programa/totalConsultas)
                    name = item.get("institucion", item.get("programa", "Desconocido"))
                    raw_val = item.get("cantidad", item.get("totalConsultas", 0))
                    
                    # Robustez: Convertir a float por si viene como string
                    try:
                        val = float(raw_val)
                    except (ValueError, TypeError):
                        val = 0
                    processed.append((str(name), val))
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    try:
                        val = float(item[1])
                    except (ValueError, TypeError):
                        val = 0
                    processed.append((str(item[0]), val))
        
        self.data = sorted(processed, key=lambda x: x[1], reverse=True)
        self.calculate_layout()
        self.update()

    def calculate_layout(self):
        # Título superior del gráfico - Definir siempre para evitar AttributeError en paintEvent
        title_height = 35
        padding = 2 # Evitar que el borde se pegue a la base
        self.draw_rect = QRectF(padding, title_height, self.width() - (padding * 2), max(1, self.height() - title_height - padding))

        if not self.data or self.width() <= 0 or self.height() <= 0:
            self.rects = []
            return

        total_value = sum(v for _, v in self.data)
        if total_value == 0:
            self.rects = []
            return

        self.rects = []
        
        self._divide_rect(
            self.draw_rect,
            self.data,
            total_value,
            0
        )

    def _divide_rect(self, rect, data, total, color_idx):
        if not data or rect.width() < 10 or rect.height() < 10:
            return

        if len(data) == 1:
            name, val = data[0]
            color = QColor(self.colors[color_idx % len(self.colors)])
            self.rects.append((rect, name, val, color))
            return

        # Dividir buscando que el ratio de aspecto sea lo más cuadrado posible
        best_mid = 1
        min_diff = float('inf')
        
        current_sum = 0
        for i in range(len(data) - 1):
            current_sum += data[i][1]
            ratio = current_sum / total
            if abs(ratio - 0.5) < min_diff:
                min_diff = abs(ratio - 0.5)
                best_mid = i + 1

        data_left = data[:best_mid]
        data_right = data[best_mid:]
        
        val_left = sum(v for _, v in data_left)
        val_right = total - val_left
        
        if val_left == 0 or val_right == 0: return

        if rect.width() > rect.height():
            w_left = rect.width() * (val_left / total)
            rect_left = QRectF(rect.x(), rect.y(), w_left, rect.height())
            rect_right = QRectF(rect.x() + w_left, rect.y(), rect.width() - w_left, rect.height())
        else:
            h_left = rect.height() * (val_left / total)
            rect_left = QRectF(rect.x(), rect.y(), rect.width(), h_left)
            rect_right = QRectF(rect.x(), rect.y() + h_left, rect.width(), rect.height() - h_left)

        self._divide_rect(rect_left, data_left, val_left, color_idx)
        self._divide_rect(rect_right, data_right, val_right, color_idx + best_mid)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Dibujar Título del gráfico
        painter.setPen(QColor("#242d8c"))
        painter.setFont(QFont("Segoe UI", 13, QFont.Bold))
        painter.drawText(QRectF(0, 0, self.width(), 30), Qt.AlignLeft | Qt.AlignVCenter, "Consultas realizadas por Institución")

        if not self.rects:
            painter.setPen(QColor("#94a3b8"))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(self.draw_rect, Qt.AlignCenter, "Sin datos para mostrar")
            return

        font_title = QFont("Segoe UI", 9, QFont.DemiBold)
        font_val = QFont("Segoe UI", 8)

        for rect, name, val, color in self.rects:
            painter.setBrush(color)
            painter.setPen(QPen(Qt.white, 1.5))
            painter.drawRect(rect)

            # Dibujar textos con margen inteligente
            if rect.width() > 50 and rect.height() > 40:
                painter.setPen(Qt.white)
                
                # Nombre Institución (Arriba Izquierda)
                painter.setFont(font_title)
                name_trimmed = name
                metrics = painter.fontMetrics()
                if metrics.horizontalAdvance(name) > rect.width() - 10:
                    name_trimmed = metrics.elidedText(name, Qt.ElideRight, int(rect.width() - 10))
                
                painter.drawText(rect.adjusted(7, 7, -5, -5), Qt.AlignLeft | Qt.AlignTop, name_trimmed)
                
                # Cantidad (Abajo Izquierda - ejemplo "mill.")
                painter.setFont(font_val)
                # Formatear número para que no muestre .0 si es entero
                f_val = f"{int(val)}" if val == int(val) else f"{val:.1f}"
                val_text = f"{f_val} mill." if val >= 1 else f"{val} unid."
                painter.drawText(rect.adjusted(7, 5, -7, -7), Qt.AlignLeft | Qt.AlignBottom, val_text)

    def mouseMoveEvent(self, event):
        """Detecta sobre qué rectángulo está el mouse y muestra tooltip personalizado."""
        pos = event.position()
        found = False
        for rect, name, val, _ in self.rects:
            if rect.contains(pos):
                # Formatear el valor con separadores de miles
                try:
                    v_formatted = f"{int(val):,}".replace(",", ".")
                except:
                    v_formatted = str(val)
                
                # Actualizar contenido del tooltip
                self.custom_tooltip.setText(f"<b style='color:#60a5fa;'>{name}</b><br/><span style='color:#94a3b8;'>Consultas:</span> <b style='color:white;'>{v_formatted}</b>")
                self.custom_tooltip.adjustSize()
                
                # Posicionar tooltip cerca del mouse pero dentro del widget
                tx = int(pos.x() + 15)
                ty = int(pos.y() + 15)
                
                # Evitar que se salga por la derecha
                if tx + self.custom_tooltip.width() > self.width():
                    tx = int(pos.x() - self.custom_tooltip.width() - 10)
                # Evitar que se salga por abajo
                if ty + self.custom_tooltip.height() > self.height():
                    ty = int(pos.y() - self.custom_tooltip.height() - 10)
                
                self.custom_tooltip.move(tx, ty)
                self.custom_tooltip.setVisible(True)
                self.custom_tooltip.raise_()
                found = True
                break
        
        if not found:
            self.custom_tooltip.setVisible(False)
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        """Asegura que el tooltip se oculte al salir del widget."""
        self.custom_tooltip.setVisible(False)
        super().leaveEvent(event)

    def resizeEvent(self, event):
        self.calculate_layout()
        super().resizeEvent(event)


class PieChartWidget(QFrame):
    def __init__(self, title, data=None, colors=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150) # Reducido un poco para permitir que crezca el gráfico
        self.setStyleSheet("QFrame { background-color: transparent; border: none; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.series = QPieSeries()
        self.series.setHoleSize(0.45)  # Mayor grosor del donut
        self.series.setPieSize(0.85)   # Reducir un poco para dar espacio a la leyenda
        
        self.chart = QChart()
        self.chart.addSeries(self.series)
        self.chart.setTitle(title)
        self.chart.setAnimationOptions(QChart.SeriesAnimations)
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)
        
        # Aumentar tamaño de fuente de la leyenda
        legend_font = self.chart.legend().font()
        legend_font.setPointSize(11)
        legend_font.setBold(True)
        self.chart.legend().setFont(legend_font)
        
        self.chart.setBackgroundVisible(False)
        # Margen inferior de 15px para "bajar" más la leyenda
        self.chart.setMargins(QMargins(0, 0, 0, 15)) 
        self.chart.setBackgroundRoundness(0)
        self.chart.layout().setContentsMargins(0, 0, 0, 0)

        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        self.chart_view.setStyleSheet("background: transparent;")
        
        # UX: Hacer que el gráfico use todo el espacio disponible
        self.chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        layout.addWidget(self.chart_view)

        if data:
            self.update_data(data, colors)

    def update_data(self, data, colors=None):
        self.series.clear()
        total = sum(v for _, v in data)
        if total == 0:
            return
        for i, (label, value) in enumerate(data):
            s = self.series.append(f"{label} ({value})", value)
            if colors and i < len(colors):
                s.setBrush(QColor(colors[i]))
            s.setLabelVisible(False)
            s.hovered.connect(lambda state, sl=s: sl.setExploded(state))


class DashboardCard(QFrame):
    def __init__(self, title, value, color="#2563eb", has_chart=True, value_top=False, parent=None):
        super().__init__(parent)
        # KPI simples son más pequeñas ahora
        if not has_chart:
            self.setMinimumHeight(110)
            self.setMaximumHeight(130)
        else:
            self.setMinimumHeight(280)
            self.setMaximumHeight(350)
            
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border: 1px solid #e2e8f0;
                border-left: 4px solid {color};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 10))
        self.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(2)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("color: #64748b; font-size: 11px; font-weight: 700; text-transform: none; border: none;")

        self.value_lbl = QLabel(str(value))
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: 800; border: none;")

        if value_top:
            layout.addWidget(self.value_lbl)
            layout.addWidget(self.title_lbl)
        else:
            layout.addWidget(self.title_lbl)
            layout.addWidget(self.value_lbl)

        if has_chart:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("background-color: #f1f5f9; min-height: 1px; border: none; margin: 5px 0;")
            layout.addWidget(line)

            self.pie = PieChartWidget("", parent=self)
            layout.addWidget(self.pie)
            layout.addStretch()
        else:
            self.pie = None
            layout.addStretch()

    def update_value(self, value):
        self.value_lbl.setText(str(value))

    def update_pie(self, data, colors=None):
        if self.pie:
            self.pie.update_data(data, colors)


def _make_section_title(text):
    lbl = QLabel(text)
    lbl.setStyleSheet("""
        font-size: 20px;
        font-weight: 800;
        color: #0f172a;
        margin: 0;
    """)
    return lbl


class DashboardView(QWidget):
    def __init__(self, viewmodel, parent=None):
        super().__init__(parent)
        self.viewmodel = viewmodel
        self.setObjectName("dashboardView")
        self.setStyleSheet("background-color: #f1f5f9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Splitter Vertical
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setHandleWidth(6)
        self.splitter.setStyleSheet("""
            QSplitter::handle { 
                background-color: #cbd5e1; 
                margin: 2px 0;
            }
            QSplitter::handle:hover { background-color: #94a3b8; }
        """)
        main_layout.addWidget(self.splitter)

        # --- SECCIÓN 1: Estadísticas SINGDAP ---
        container1 = QWidget()
        container1.setMinimumHeight(350) # Reducido para mayor flexibilidad
        layout1 = QVBoxLayout(container1)
        layout1.setContentsMargins(25, 20, 25, 10)
        layout1.setSpacing(10)

        header1 = QHBoxLayout()
        header1.addWidget(_make_section_title("Estadísticas SINGDAP"))
        header1.addStretch()
        
        self.updated_lbl = QLabel("Cargando...")
        self.updated_lbl.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")
        header1.addWidget(self.updated_lbl)

        self.refresh_btn = QPushButton("Actualizar")
        self.refresh_btn.setObjectName("primaryButton")
        self.refresh_btn.setFixedSize(100, 32)
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.viewmodel.cargar_estadisticas)
        header1.addWidget(self.refresh_btn)
        
        layout1.addLayout(header1)

        # Grid reorganizado para que las tarjetas simples sean pequeñas y Riesgos use el espacio
        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(grid_container)
        self.grid.setSpacing(15)
        self.grid.setContentsMargins(0, 5, 0, 5)

        # Inicializar Tarjetas
        self.card_activos = DashboardCard("Resumen Activos", "0", "#2563eb", has_chart=False)
        self.card_rat = DashboardCard("Resumen RAT", "0", "#10b981", has_chart=False)
        self.card_eipd = DashboardCard("Resumen EIPD", "0", "#f59e0b", has_chart=False)
        self.card_riesgos = DashboardCard("Alertas de Riesgo", "0", "#ef4444", has_chart=True)

        # Layout mejorado:
        # Columna de la izquierda para las 3 tarjetas simples apiladas
        left_vbox = QVBoxLayout()
        left_vbox.setSpacing(10)
        left_vbox.addWidget(self.card_activos)
        left_vbox.addWidget(self.card_rat)
        left_vbox.addWidget(self.card_eipd)
        left_vbox.addStretch()
        
        left_widget = QWidget()
        left_widget.setLayout(left_vbox)
        
        # Colocar en el grid principal de la sección
        self.grid.addWidget(left_widget, 0, 0)
        self.grid.addWidget(self.card_riesgos, 0, 1)
        
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        # Añadir el contenedor de grid directamente al layout principal de la sección (sin scroll)
        layout1.addWidget(grid_container)
        
        self.splitter.addWidget(container1)

        # --- SECCIÓN 2: Estadísticas por Usuario (TREEMAP) ---
        container2 = QWidget()
        container2.setMinimumHeight(250)
        layout2 = QVBoxLayout(container2)
        layout2.setContentsMargins(25, 10, 25, 20)
        layout2.setSpacing(10)

        header2 = QHBoxLayout()
        header2.addWidget(_make_section_title("Estadísticas por Usuario"))
        header2.addStretch()

        self.inst_status = QLabel("")
        self.inst_status.setStyleSheet("font-size: 11px; color: #64748b; font-style: italic;")
        header2.addWidget(self.inst_status)

        self.refresh_inst = QPushButton("Recargar")
        self.refresh_inst.setObjectName("secondaryButton")
        self.refresh_inst.setFixedSize(90, 32)
        self.refresh_inst.setCursor(Qt.PointingHandCursor)
        self.refresh_inst.clicked.connect(lambda: self.viewmodel.cargar_instituciones(force_api=True))
        header2.addWidget(self.refresh_inst)
        
        layout2.addLayout(header2)

        # KPIs adicionales sobre el TreeMap (Restaurados)
        kpi_inst_layout = QHBoxLayout()
        kpi_inst_layout.setSpacing(15)
        self.card_inst_count = DashboardCard("Instituciones distintas", "0", "#6366f1", has_chart=False, value_top=True)
        self.card_total_queries = DashboardCard("Consultas realizadas", "0", "#334155", has_chart=False, value_top=True)
        
        kpi_inst_layout.addWidget(self.card_inst_count)
        kpi_inst_layout.addWidget(self.card_total_queries)
        
        # Contenedor directo sin scroll
        layout2.addLayout(kpi_inst_layout)

        self.treemap = TreeMapWidget()
        self.treemap.setStyleSheet("background-color: white; border-radius: 10px; border: 1px solid #e2e8f0; padding: 10px;")
        layout2.addWidget(self.treemap)

        self.splitter.addWidget(container2)
        
        # Proporción balanceada: Permitir que el splitter distribuya el espacio dinámicamente
        self.splitter.setSizes([400, 600])

        self.loading = LoadingOverlay(self)

        # Conexiones
        self.viewmodel.on_loading.connect(self.loading.setVisible)
        self.viewmodel.on_stats_ready.connect(self._on_stats_received)
        self.viewmodel.on_error.connect(lambda e: self.updated_lbl.setText(f"Error: {e}"))
        self.viewmodel.on_instituciones_ready.connect(self._on_inst_received)
        self.viewmodel.on_instituciones_error.connect(lambda e: self.inst_status.setText(f"Error: {e}"))

        # Cargas iniciales
        QTimer.singleShot(300, self.viewmodel.cargar_estadisticas)
        QTimer.singleShot(600, lambda: self.viewmodel.cargar_instituciones(force_api=True))

    @Slot(dict)
    def _on_stats_received(self, data):
        from datetime import datetime
        self.updated_lbl.setText(f"Act: {datetime.now().strftime('%H:%M:%S')}")

        activos = data.get("total_inventario", 0)
        self.card_activos.update_value(activos)

        rat = data.get("total_rat", 0)
        self.card_rat.update_value(rat)

        eipd = data.get("total_eipd", 0)
        self.card_eipd.update_value(eipd)

        riesgos = data.get("riesgos", {})
        t_riesgos = riesgos.get("total", 0)
        self.card_riesgos.update_value(t_riesgos)
        if t_riesgos > 0:
            self.card_riesgos.update_pie([
                ("Subsanados", riesgos.get("subsanados", 0)),
                ("Pendientes", riesgos.get("pendientes", 0))
            ], ["#10b981", "#ef4444"])

    @Slot(object)
    def _on_inst_received(self, data):
        from datetime import datetime
        print(f"DEBUG DASHBOARD: Datos recibidos para instituciones (tipo: {type(data)}): {data}")
        self.inst_status.setText(f"Act: {datetime.now().strftime('%H:%M:%S')}")

        list_data = []
        if isinstance(data, dict):
            if "consultasInstituciones" in data:
                list_data = data["consultasInstituciones"]
            elif "consultasPorPrograma" in data:
                list_data = data["consultasPorPrograma"]
            else:
                print(f"DEBUG DASHBOARD: Dict no contiene claves esperadas. Claves: {list(data.keys())}")
        elif isinstance(data, list):
            list_data = data
        
        if not list_data:
            print("DEBUG DASHBOARD: No se encontraron datos válidos en la respuesta, manteniendo vista actual.")
            return # NO borrar el gráfico si la respuesta viene vacía o inválida
        
        # Calcular Totales para los nuevos KPIs
        inst_count = len(list_data)
        total_q = 0
        for item in list_data:
            if isinstance(item, dict):
                val = item.get("cantidad", item.get("totalConsultas", 0))
                try: total_q += float(val)
                except: pass
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                try: total_q += float(item[1])
                except: pass
        
        self.card_inst_count.update_value(inst_count)
        
        # Formatear total de consultas (ej. 5 mill. o número crudo)
        if total_q >= 1000000:
            total_text = f"{total_q/1000000:.1f} mill."
        else:
            total_text = f"{int(total_q)}"
        self.card_total_queries.update_value(total_text)

        self.treemap.setData(list_data)

    def resizeEvent(self, event):
        if hasattr(self, 'loading'):
            self.loading.resize(event.size())
        super().resizeEvent(event)
