import sys
import re
from pathlib import Path
from PySide6.QtGui import QIcon


def resource_base() -> Path:
    """
    Devuelve la carpeta base REAL de recursos.
    Funciona en desarrollo y en PyInstaller (--onefile).
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "src" / "resources"
    return Path(__file__).parent / "src" / "resources"


def resource_path(relative_path: str) -> Path:
    """
    Devuelve la ruta absoluta a un recurso.
    Tolera rutas con o sin 'src/resources'.
    """
    base = resource_base()
    p = Path(relative_path)

    parts = list(p.parts)
    while parts[:2] == ["src", "resources"]:
        parts = parts[2:]

    return base.joinpath(*parts)


def load_styles(app):
    """
    Carga el QSS NORMALIZANDO TODAS las rutas automáticamente.
    NO requiere modificar el QSS ni buscar iconos.
    """
    base = resource_base()
    qss_path = base / "styles.qss"

    qss = qss_path.read_text(encoding="utf-8")

    qss = re.sub(
        r'url\((["\']?)(?:src/resources/)+',
        r'url(\1',
        qss
    )
    qss = re.sub(
        r'url\((["\']?)',
        rf'url(\1{base.as_posix()}/',
        qss
    )

    app.setStyleSheet(qss)

    


def icon(path: str) -> QIcon:
    """
    Devuelve un QIcon funcional en dev y en PyInstaller,
    sin importar si el path viene como:
    - src/resources/icons/xxx.svg
    - icons/xxx.svg
    """
    return QIcon(str(resource_path(path)))