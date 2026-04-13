"""
検索結果キャッシュ（24時間TTL）
Serper APIの呼び出し回数を削減するためのシンプルなメモリキャッシュ
"""
import time
from typing import Any, Optional


class SearchCache:
    """
    シンプルなインメモリキャッシュ
    TTL: 24時間（86400秒）
    """

    def __init__(self, ttl: int = 86400):
        self._ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expire_at)

    def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        value, expire_at = self._store[key]
        if time.time() > expire_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.time() + self._ttl)

    def clear_expired(self) -> None:
        now = time.time()
        expired_keys = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired_keys:
            del self._store[k]

    def clear(self) -> int:
        """全エントリを削除し、削除した件数を返す。"""
        count = len(self._store)
        self._store.clear()
        return count

    def size(self) -> int:
        """現在のエントリ数を返す。"""
        return len(self._store)
