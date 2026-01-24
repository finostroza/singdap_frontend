import json
import os
from PySide6.QtCore import QStandardPaths, QDateTime, Qt, QMutex, QMutexLocker

class CacheManager:
    _instance = None
    _lock = QMutex()

    def __new__(cls):
        if cls._instance is None:
            with QMutexLocker(cls._lock):
                if cls._instance is None:
                    cls._instance = super(CacheManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.cache_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.cache_file = os.path.join(self.cache_dir, "catalog_cache.json")
        self.ttl_minutes = 24 * 60  # 24 hours
        self.mutex = QMutex()
        self._initialized = True
        print(f"CacheManager initialized at: {self.cache_file}")

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_cache(self, cache_data):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)
        except OSError:
            pass

    def get(self, key):
        locker = QMutexLocker(self.mutex)
        cache = self._load_cache()
        if key in cache:
            entry = cache[key]
            # ... existing logic ...
            stored_ts = entry.get("timestamp")
            if stored_ts:
                dt_stored = QDateTime.fromString(stored_ts, Qt.ISODate)
                if dt_stored.isValid() and dt_stored.addSecs(self.ttl_minutes * 60) > QDateTime.currentDateTime():
                    return entry.get("data")
        return None

    def set(self, key, data):
        locker = QMutexLocker(self.mutex)
        cache = self._load_cache()
        cache[key] = {
            "timestamp": QDateTime.currentDateTime().toString(Qt.ISODate),
            "data": data
        }
        self._save_cache(cache)

    def clear(self):
        locker = QMutexLocker(self.mutex)
        if os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
            except OSError:
                pass
