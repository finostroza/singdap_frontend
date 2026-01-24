import os
import threading
import queue
import time
from datetime import datetime
import traceback

class LoggerService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LoggerService, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Log")
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.event_file = None
        self.error_file = None
        self.username = "unknown"
        
        # Queue for fire-and-forget
        self.log_queue = queue.Queue()
        self.running = True
        
        # Background worker
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()
        
        self._initialized = True

    def init_session(self, username):
        # Extract user part from email if current is email
        if "@" in username:
            self.username = username.split("@")[0]
        else:
            self.username = username
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        self.event_file = os.path.join(self.log_dir, f"{self.username}_{timestamp}_LogEvent.log")
        self.error_file = os.path.join(self.log_dir, f"{self.username}_{timestamp}_LogError.log")

    def log_event(self, message):
        """High level executive summary event"""
        self.log_queue.put(("event", message))

    def log_error(self, message, error=None):
        """Detailed error log with possible cause"""
        self.log_queue.put(("error", message, error))

    def _process_queue(self):
        while self.running:
            try:
                item = self.log_queue.get()
                if item is None:
                    continue
                
                log_type = item[0]
                
                if log_type == "event":
                    self._write_event(item[1])
                elif log_type == "error":
                    self._write_error(item[1], item[2])
                    
                self.log_queue.task_done()
            except Exception:
                # Failsafe: logger shouldn't crash app
                pass

    def _write_event(self, message):
        if not self.event_file: return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] {message}\n"
        
        try:
            with open(self.event_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except:
            pass

    def _determine_cause(self, error):
        error_str = str(error).lower()
        if "connection" in error_str or "refused" in error_str:
            return "Posible falla de internet o el servidor backend no está respondiendo."
        if "401" in error_str or "unauthorized" in error_str:
            return "La sesión del usuario ha expirado o las credenciales son inválidas."
        if "403" in error_str or "forbidden" in error_str:
            return "El usuario no tiene permisos suficientes para realizar esta acción."
        if "404" in error_str:
            return "El recurso solicitado no fue encontrado en el servidor."
        if "500" in error_str:
            return "Error interno del servidor (bug en backend)."
        if "timeout" in error_str:
            return "El servidor tardó demasiado en responder."
        return "Error técnico no identificado, requiere revisión de logs detallados."

    def _write_error(self, message, error):
        if not self.error_file: return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cause = self._determine_cause(error) if error else "N/A"
        error_detail = str(error) if error else "Sin detalle técnico"
        
        entry = (
            f"[{timestamp}] ERROR: {message}\n"
            f"    -> Detalle Técnico: {error_detail}\n"
            f"    -> Causa Probable: {cause}\n"
            f"{'-'*50}\n"
        )
        
        try:
            with open(self.error_file, "a", encoding="utf-8") as f:
                f.write(entry)
        except:
            pass
