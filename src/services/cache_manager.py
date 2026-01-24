import json
import os
from PySide6.QtCore import QStandardPaths, QDateTime, Qt, QMutex, QMutexLocker

class CacheManager:
    def __init__(self):
        self.cache_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        self.cache_file = os.path.join(self.cache_dir, "catalog_cache.json")
        self.ttl_minutes = 24 * 60  # 24 hours
        self.mutex = QMutex()

    def _load_cache(self):
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Cache load error: {e}")
            return {}

    def _save_cache(self, cache_data):
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)
        except Exception as e:
            print(f"Cache save error: {e}")

    def get(self, key):
        with QMutexLocker(self.mutex):
            cache = self._load_cache()
            if key in cache:
                entry = cache[key]
                timestamp = entry.get("timestamp")
                if timestamp:
                    try:
                        # Fix: Check if timestamp is ISO string (legacy/buggy cache) or seconds since epoch
                        if isinstance(timestamp, str) and 'T' in timestamp:
                            saved_time = QDateTime.fromString(timestamp, Qt.ISODate)
                        else:
                            # Handle both int and float timestamps (even if stringified)
                            saved_time = QDateTime.fromSecsSinceEpoch(int(float(timestamp)))
                        
                        if saved_time.isValid() and saved_time.secsTo(QDateTime.currentDateTime()) < self.ttl_minutes * 60:
                            return entry.get("data")
                    except Exception as e:
                        print(f"Cache timestamp error: {e}")
                        # If timestamp is bad, ignore cache entry
                        pass
            return None

    def set(self, key, data):
        with QMutexLocker(self.mutex):
            cache = self._load_cache()
            cache[key] = {
                "timestamp": QDateTime.currentDateTime().toSecsSinceEpoch(),
                "data": data
            }
            self._save_cache(cache)

    def clear(self):
        with QMutexLocker(self.mutex):
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
