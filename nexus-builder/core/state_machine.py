import json
import time
from typing import TypedDict
from core.llm_client import LLMClient
from core.tools.registry import tool_registry
from core.logger import logger
from core.skill_manager import skill_manager


class AgentState(TypedDict):
    user_input: str
    analysis: str
    route: str
    execution_result: str
    critique: str
    final_response: str
    iteration: int
    is_finished: bool
    active_skill: str  # имя совпавшего навыка, или ""


_TOOL_NAMES = ["file_writer", "web_search", "code_executor", "project_builder", "shell_executor"]
_BUILD_VERBS = ["создай", "сделай", "напиши", "сгенерируй", "разработай", "create", "make", "build", "generate"]
_BUILD_TARGETS = ["бот", "сайт", "сервис", "приложен", "telegram", "tg", "api", "скрипт", "программ", "webapp", "веб"]


class OrchestratorStateMachine:
    def __init__(self, llm_client: LLMClient, max_iterations: int = 3):
        self.llm = llm_client
        self.max_iterations = max_iterations
        self.total_cost = 0.0

    def run(self, user_input: str) -> str:
        start_time = time.time()
        self.total_cost = 0.0
        state: AgentState = {
            "user_input": user_input,
            "analysis": "",
            "route": "",
            "execution_result": "",
            "critique": "",
            "final_response": "",
            "iteration": 0,
            "is_finished": False,
            "active_skill": "",
        }
        print(f"[Orchestrator] Start: {user_input[:60]}...")

        while not state["is_finished"] and state["iteration"] < self.max_iterations:
            state["iteration"] += 1
            print(f"[Orchestrator] Итерация {state['iteration']}/{self.max_iterations}")
            state = self._analyze(state)
            state = self._route(state)
            state = self._execute(state)
            state = self._critique(state)

            if any(w in state["critique"].lower() for w in ["да", "yes", "ok", "good", "достаточно", "отлично"]):
                state["is_finished"] = True
                state = self._finish(state)
            elif state["iteration"] >= self.max_iterations:
                state["is_finished"] = True
                state["final_response"] = state["execution_result"]
                if state["active_skill"]:
                    skill_manager.update_success_rate(state["active_skill"], False)

        duration = time.time() - start_time
        success = state["is_finished"]
        logger.log_request(
            user_input=state["user_input"],
            route=state["route"],
            execution_result=state["execution_result"],
            iterations=state["iteration"],
            duration=duration,
            cost=self.total_cost,
            success=success,
        )
        print(f"[Orchestrator] Готово за {duration:.2f}с | итерации: {state['iteration']} | {self.total_cost:.4f}₽")
        return state["final_response"]

    # ──────────────────────────────────────────────
    # Шаги ReAct-цикла
    # ──────────────────────────────────────────────

    def _analyze(self, state: AgentState) -> AgentState:
        # Если есть активный навык — используем его system_prompt
        sys_prompt = None
        if state["active_skill"]:
            sk = skill_manager.skills.get(state["active_skill"])
            if sk and sk.system_prompt:
                sys_prompt = sk.system_prompt

        prompt = (
            f"Анализ запроса:\n<request>{state['user_input']}</request>\n"
            f"Доступные инструменты:\n{tool_registry.get_all_descriptions()}"
        )
        if state["iteration"] > 1:
            prompt += f"\nПредыдущая критика: {state['critique']}"

        state["analysis"], cost = self.llm.ask(prompt, system_prompt=sys_prompt)
        self.total_cost += cost
        print(f"  -> Анализ: {state['analysis'][:60]}...")
        return state

    def _route(self, state: AgentState) -> AgentState:
        # На первой итерации проверяем навыки
        if state["iteration"] == 1:
            skill = skill_manager.find_matching(state["user_input"])
            if skill:
                state["route"] = skill.tool
                state["active_skill"] = skill.name
                print(f"  -> Навык: {skill.name} → {skill.tool}")
                return state

        u = state["user_input"].lower()

        if any(w in u for w in ["pip install", "установи пакет", "install package", "запусти проект"]):
            state["route"] = "shell_executor"
        elif self._is_build_request(u):
            state["route"] = "project_builder"
        elif any(w in u for w in ["найди", "поиск", "search", "интернет", "кто такой", "что такое", "информация о"]):
            state["route"] = "web_search"
        elif any(w in u for w in ["сохрани", "файл", "запиши", "документ", "save", "file", "write"]):
            state["route"] = "file_writer"
        elif any(w in u for w in ["выполни", "код", "calculate", "execute", "посчитай"]):
            state["route"] = "code_executor"
        else:
            prompt = (
                f"Выбери строго одно: 'answer' или один из {_TOOL_NAMES}. "
                f"Запрос: <request>{state['user_input']}</request>. Ответь только одним словом."
            )
            route_raw, cost = self.llm.ask(prompt)
            self.total_cost += cost
            route_raw = route_raw.strip().lower().strip("'\"")
            state["route"] = route_raw if route_raw in _TOOL_NAMES else "answer"

        print(f"  -> Маршрут: {state['route']}")
        return state

    def _execute(self, state: AgentState) -> AgentState:
        route = state["route"]

        if route == "answer":
            state["execution_result"], cost = self.llm.ask(
                f"Краткий ответ только по сути:\n<request>{state['user_input']}</request>\n"
                f"Анализ: {state['analysis']}"
            )
            self.total_cost += cost

        elif route == "web_search":
            prompt = (
                f"Extract the main topic and create a precise English search query (2-4 words). "
                f"Request: <request>{state['user_input']}</request>. Return ONLY the query."
            )
            query, cost = self.llm.ask(prompt)
            self.total_cost += cost
            res = tool_registry.execute("web_search", query=query.strip().strip('"\''))
            state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        elif route == "code_executor":
            prompt = (
                f"Generate Python code for:\n<request>{state['user_input']}</request>\n"
                f"Return ONLY the code, no explanations, no markdown fences."
            )
            code, cost = self.llm.ask(prompt)
            self.total_cost += cost
            res = tool_registry.execute("code_executor", code=self._strip_md(code))
            state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        elif route == "file_writer":
            prompt = f"Generate content to save for:\n<request>{state['user_input']}</request>"
            content, cost = self.llm.ask(prompt)
            self.total_cost += cost
            res = tool_registry.execute("file_writer", file_path="agent_result.txt", content=content, mode="w")
            state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        elif route == "project_builder":
            state = self._execute_project_builder(state)

        elif route == "shell_executor":
            prompt = (
                f"What shell command should be run for:\n<request>{state['user_input']}</request>\n"
                f"Allowed: pip, pip3, python, python3, npm, node, ls.\n"
                f"Return ONLY the command."
            )
            command, cost = self.llm.ask(prompt)
            self.total_cost += cost
            res = tool_registry.execute("shell_executor", command=command.strip())
            state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        else:
            res = tool_registry.execute(route, query=state["user_input"])
            state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        print(f"  -> Результат: {state['execution_result'][:80]}...")
        return state

    def _execute_project_builder(self, state: AgentState) -> AgentState:
        prompt = (
            f"Generate a complete working project for this request:\n"
            f"<request>{state['user_input']}</request>\n\n"
            f"Return ONLY a valid JSON object (no markdown, no comments):\n"
            f'{{"project_name": "name_snake_case", "files": {{"main.py": "full code", "requirements.txt": "dep1\\ndep2"}}}}\n\n'
            f"Rules:\n"
            f"- project_name must be short snake_case\n"
            f"- For Telegram bots: use aiogram 3.x, read token from env BOT_TOKEN\n"
            f"- For web apps: use Flask or FastAPI\n"
            f"- All files must be complete and runnable"
        )
        raw, cost = self.llm.ask(prompt, max_tokens=3000)
        self.total_cost += cost

        raw = self._strip_md(raw)
        try:
            data = json.loads(raw)
            project_name = data.get("project_name", "new_project")
            files = data.get("files", {})
            if not files:
                raise ValueError("empty files")
        except (json.JSONDecodeError, ValueError):
            project_name = "new_project"
            files = {"main.py": raw}

        res = tool_registry.execute("project_builder", project_name=project_name, files=files)
        state["execution_result"] = f"OK: {res['result']}" if res["success"] else f"Error: {res['error']}"

        if res["success"] and "requirements.txt" in files and files["requirements.txt"].strip():
            pip_res = tool_registry.execute(
                "shell_executor",
                command=f"pip install -r output/projects/{project_name}/requirements.txt",
            )
            if pip_res["success"]:
                state["execution_result"] += "\nЗависимости установлены."
            else:
                state["execution_result"] += f"\nОшибка установки: {pip_res['error'][:100]}"

        return state

    def _critique(self, state: AgentState) -> AgentState:
        prompt = (
            "Ты — критик. Оцени, решает ли результат задачу пользователя.\n"
            f"Запрос: <request>{state['user_input']}</request>\n"
            f"Результат: <result>{state['execution_result'][:500]}</result>\n"
            "Если результат решает задачу — ответь 'Да'. Если нет — 'Нет'. Одно слово."
        )
        state["critique"], cost = self.llm.ask(prompt)
        self.total_cost += cost
        print(f"  -> Критика: {state['critique'][:30]}")
        return state

    def _finish(self, state: AgentState) -> AgentState:
        state["final_response"], cost = self.llm.ask(
            f"Дай итоговый краткий ответ пользователю ТОЛЬКО по сути:\n"
            f"<result>{state['execution_result']}</result>"
        )
        self.total_cost += cost

        # Обновление навыков
        if state["active_skill"]:
            skill_manager.update_success_rate(state["active_skill"], True)
        else:
            self._try_generate_skill(state)

        return state

    # ──────────────────────────────────────────────
    # Автогенерация навыков
    # ──────────────────────────────────────────────

    def _try_generate_skill(self, state: AgentState):
        """После N успешных выполнений одного типа генерирует навык через LLM."""
        route = state["route"]
        if route == "answer":
            return

        try:
            cursor = logger.conn.execute(
                "SELECT COUNT(*) FROM requests WHERE route=? AND success=1", (route,)
            )
            success_count = cursor.fetchone()[0]
        except Exception:
            return

        if not skill_manager.should_generate(route, success_count):
            return

        # Генерируем оптимизированный system_prompt через LLM
        prompt = (
            f"Based on this successful task, write a concise system prompt (2-3 sentences) "
            f"that would help generate better results for similar tasks in the future.\n"
            f"Tool: {route}\n"
            f"Example request: {state['user_input'][:200]}\n"
            f"Example result: {state['final_response'][:200]}\n"
            f"Return ONLY the system prompt."
        )
        sys_prompt, cost = self.llm.ask(prompt)
        self.total_cost += cost

        # Ключевые слова — значимые слова из запроса (длиннее 3 символов)
        words = [w for w in state["user_input"].lower().split() if len(w) >= 4][:6]
        skill_name = f"{route}_{'_'.join(words[:2])}"

        skill_manager.save_skill(
            name=skill_name,
            keywords=words,
            system_prompt=sys_prompt,
            tool=route,
            example_input=state["user_input"],
            example_output=state["final_response"],
        )
        print(f"[Orchestrator] Навык сгенерирован: {skill_name}")

    # ──────────────────────────────────────────────
    # Утилиты
    # ──────────────────────────────────────────────

    @staticmethod
    def _is_build_request(text: str) -> bool:
        has_verb = any(v in text for v in _BUILD_VERBS)
        has_target = any(t in text for t in _BUILD_TARGETS)
        return has_verb and has_target

    @staticmethod
    def _strip_md(text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
