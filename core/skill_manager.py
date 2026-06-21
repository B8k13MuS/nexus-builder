import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"
SKILL_GEN_THRESHOLD = 3  # Кол-во успехов для генерации навыка


class Skill:
    """Навык — сохранённый оптимизированный паттерн для типа запросов."""

    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.keywords: list[str] = data.get("keywords", [])
        self.system_prompt: str = data.get("system_prompt", "")
        self.tool: str = data.get("tool", "answer")
        self.uses: int = data.get("uses", 0)
        self.success_rate: float = data.get("success_rate", 1.0)
        self.examples: list[dict] = data.get("examples", [])

    def matches(self, text: str) -> bool:
        t = text.lower()
        return any(kw.lower() in t for kw in self.keywords)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "keywords": self.keywords,
            "system_prompt": self.system_prompt,
            "tool": self.tool,
            "uses": self.uses,
            "success_rate": round(self.success_rate, 3),
            "examples": self.examples,
        }


class SkillManager:
    """
    Хранит и применяет навыки агента.

    Навык создаётся автоматически после SKILL_GEN_THRESHOLD успешных выполнений
    одного типа задачи. LLM генерирует оптимизированный system_prompt на основе
    накопленных примеров.

    При следующем похожем запросе:
    - route определяется мгновенно (без LLM-роутинга)
    - в _analyze используется оптимизированный system_prompt навыка
    """

    def __init__(self):
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self.skills: dict[str, Skill] = {}
        self._load_all()

    # ──────────────────────────────────────────────
    # Загрузка
    # ──────────────────────────────────────────────

    def _load_all(self):
        for path in SKILLS_DIR.glob("*.json"):
            if path.name == "security_rules.json":
                continue
            try:
                skill = Skill(json.loads(path.read_text(encoding="utf-8")))
                self.skills[skill.name] = skill
                logger.info(f"[Skills] Загружен: {skill.name} (uses={skill.uses}, rate={skill.success_rate:.2f})")
            except Exception as e:
                logger.error(f"[Skills] Ошибка загрузки {path.name}: {e}")

    # ──────────────────────────────────────────────
    # Поиск
    # ──────────────────────────────────────────────

    def find_matching(self, text: str) -> Optional[Skill]:
        """Возвращает лучший навык для текста (по uses, только высококачественные)."""
        candidates = [
            s for s in self.skills.values()
            if s.matches(text) and s.success_rate >= 0.5
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda s: s.uses * s.success_rate)

    # ──────────────────────────────────────────────
    # Сохранение и обновление
    # ──────────────────────────────────────────────

    def save_skill(
        self,
        name: str,
        keywords: list[str],
        system_prompt: str,
        tool: str,
        example_input: str,
        example_output: str,
    ) -> str:
        safe = "".join(c for c in name if c.isalnum() or c in "_-").lower()[:40] or "skill"

        if safe in self.skills:
            sk = self.skills[safe]
            sk.uses += 1
            new_kw = [k for k in keywords if k not in sk.keywords]
            sk.keywords = (sk.keywords + new_kw)[:20]
            if system_prompt and len(system_prompt) > len(sk.system_prompt):
                sk.system_prompt = system_prompt
            if len(sk.examples) < 10:
                sk.examples.append({"in": example_input[:300], "out": example_output[:300]})
        else:
            sk = Skill({
                "name": safe,
                "keywords": keywords[:15],
                "system_prompt": system_prompt,
                "tool": tool,
                "uses": 1,
                "success_rate": 1.0,
                "examples": [{"in": example_input[:300], "out": example_output[:300]}],
            })
            self.skills[safe] = sk

        self._persist(sk)
        logger.info(f"[Skills] Сохранён: {safe} (uses={sk.uses})")
        return safe

    def update_success_rate(self, skill_name: str, success: bool):
        """Обновляет рейтинг навыка (экспоненциальное скользящее среднее)."""
        sk = self.skills.get(skill_name)
        if not sk:
            return
        sk.uses += 1
        sk.success_rate = sk.success_rate * 0.8 + (1.0 if success else 0.0) * 0.2
        self._persist(sk)

    def _persist(self, sk: Skill):
        path = SKILLS_DIR / f"{sk.name}.json"
        path.write_text(json.dumps(sk.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    # ──────────────────────────────────────────────
    # Утилиты
    # ──────────────────────────────────────────────

    def should_generate(self, route: str, success_count: int) -> bool:
        return (
            route not in ("answer",)
            and success_count > 0
            and success_count % SKILL_GEN_THRESHOLD == 0
        )

    def list_skills(self) -> str:
        if not self.skills:
            return "Навыков пока нет."
        lines = []
        for sk in sorted(self.skills.values(), key=lambda s: s.uses, reverse=True):
            lines.append(
                f"• {sk.name}  uses={sk.uses}  rate={sk.success_rate:.0%}  tool={sk.tool}"
            )
        return "\n".join(lines)


skill_manager = SkillManager()
