from PySide6.QtCore import QRunnable, Slot, QObject, Signal

class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)
    result = Signal(object)

class ComboLoaderRunnable(QRunnable):
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        print(f"[WORKER START] Loading data via background thread...")
        try:
            result = self.func(*self.args, **self.kwargs)
            print(f"[WORKER SUCCESS] Data loaded successfully.")
            self.signals.result.emit(result)
        except Exception as e:
            print(f"[WORKER ERROR] Failed to load data: {str(e)}")
            self.signals.error.emit(str(e))
        finally:
            self.signals.finished.emit(None)
