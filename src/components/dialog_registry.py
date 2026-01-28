from src.components.activo_dialog import ActivoDialog
from src.components.eipd_dialog import EipdDialog
from src.components.rat_dialog import RatDialog

DIALOG_REGISTRY = {
    "ActivoDialog": ActivoDialog,
    "EipdDialog": EipdDialog,
    "RatDialog": RatDialog,
}

def get_dialog_class(name: str):
    return DIALOG_REGISTRY.get(name)
