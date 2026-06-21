import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Set

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).resolve().parents[1] / "skills" / "security_rules.json"

# Статические паттерны инъекций / prompt-injection атак
_STATIC_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "forget your instructions",
    "you are now",
    "act as if",
    "jailbreak",
    "pretend you are",
    "rm -rf",
    "drop table",
    "'; select",
    "<script>",
    "javascript:",
    "__import__",
    "os.system(",
    "subprocess.call(",
    "eval(base64",
    "exec(base64",
]


class SecurityGuard:
    """
    Защита бота:
    - Whitelist пользователей (ALLOWED_USER_IDS)
    - Rate limiting (MAX запросов за WINDOW секунд)
    - Блокировка инъекций и атак (статические + выученные паттерны)
    - Авто-обучение: паттерн, встретившийся 3+ раз → добавляется в blocklist
    """

    def __init__(
        self,
        allowed_ids: Set[int],
        owner_id: int,
        max_requests: int = 10,
        window_seconds: int = 300,
    ):
        self.allowed_ids = allowed_ids
        self.owner_id = owner_id
        self.max_requests = max_requests
        self.window = window_seconds

        self._rate_buckets: dict[int, list[float]] = defaultdict(list)
        self._learned_patterns: set[str] = set()
        self._pattern_hits: dict[str, int] = defaultdict(int)
        self._blocked_log: list[dict] = []

        self._load_rules()

    # ──────────────────────────────────────────────
    # Основная проверка
    # ──────────────────────────────────────────────

    def check(self, user_id: int, username: str = "", text: str = "") -> tuple[bool, str]:
        """
        Returns (allowed: bool, reason: str)
        reason: 'ok' | 'unauthorized' | 'rate_limit' | 'too_long' | 'injection'
        """
        # 1. Whitelist (пустой список = открытый доступ)
        if self.allowed_ids and user_id not in self.allowed_ids:
            self._record(user_id, username, "unauthorized", text)
            return False, "unauthorized"

        # 2. Rate limit
        now = time.time()
        bucket = [t for t in self._rate_buckets[user_id] if now - t < self.window]
        self._rate_buckets[user_id] = bucket
        if len(bucket) >= self.max_requests:
            self._record(user_id, username, "rate_limit", text)
            return False, "rate_limit"
        self._rate_buckets[user_id].append(now)

        # 3. Длина входа
        if len(text) > 4000:
            return False, "too_long"

        # 4. Статические паттерны
        text_lower = text.lower()
        for pattern in _STATIC_PATTERNS:
            if pattern in text_lower:
                self._record(user_id, username, f"injection:{pattern[:25]}", text)
                self._learn(text[:80])
                return False, "injection"

        # 5. Выученные паттерны
        for pattern in self._learned_patterns:
            if pattern in text_lower:
                self._record(user_id, username, f"learned:{pattern[:25]}", text)
                return False, "injection"

        return True, "ok"

    # ──────────────────────────────────────────────
    # Самообучение
    # ──────────────────────────────────────────────

    def _learn(self, text: str):
        """Запоминает повторяющиеся паттерны атак и добавляет в blocklist."""
        key = text.strip().lower()[:60]
        self._pattern_hits[key] += 1
        if self._pattern_hits[key] >= 3 and key not in self._learned_patterns:
            self._learned_patterns.add(key)
            self._save_rules()
            logger.warning(f"[Security] Выучен новый блокирующий паттерн: '{key[:40]}...'")

    # ──────────────────────────────────────────────
    # Логирование
    # ──────────────────────────────────────────────

    def _record(self, user_id: int, username: str, reason: str, text: str):
        entry = {
            "user_id": user_id,
            "username": username,
            "reason": reason,
            "text": text[:200],
            "ts": time.time(),
        }
        self._blocked_log.append(entry)
        logger.warning(f"[Security] BLOCKED uid={user_id} @{username}: {reason}")

    def get_stats(self) -> dict:
        return {
            "total_blocked": len(self._blocked_log),
            "learned_patterns": len(self._learned_patterns),
            "allowed_ids_count": len(self.allowed_ids),
        }

    def recent_blocked(self, n: int = 10) -> list[dict]:
        return self._blocked_log[-n:]

    def is_owner(self, user_id: int) -> bool:
        return user_id == self.owner_id

    # ──────────────────────────────────────────────
    # Персистентность правил
    # ──────────────────────────────────────────────

    def _load_rules(self):
        if _RULES_PATH.exists():
            try:
                data = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
                self._learned_patterns = set(data.get("learned_patterns", []))
                self._pattern_hits = defaultdict(int, data.get("pattern_hits", {}))
                logger.info(f"[Security] Загружено выученных паттернов: {len(self._learned_patterns)}")
            except Exception as e:
                logger.error(f"[Security] Ошибка загрузки правил: {e}")

    def _save_rules(self):
        _RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "learned_patterns": sorted(self._learned_patterns),
            "pattern_hits": dict(self._pattern_hits),
        }
        _RULES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
