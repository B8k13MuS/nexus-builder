from typing import TypedDict
import json
import time
from core.llm_client import LLMClient
from core.tools.registry import tool_registry
from core.logger import logger

class AgentState(TypedDict):
    user_input: str
    analysis: str
    route: str
    execution_result: str
    critique: str
    final_response: str
    iteration: int
    is_finished: bool

class OrchestratorStateMachine:
    def __init__(self, llm_client: LLMClient, max_iterations: int = 3):
        self.llm = llm_client
        self.max_iterations = max_iterations
        self.tools_desc = tool_registry.get_all_descriptions()
        self.tool_names = ['file_writer', 'web_search', 'code_executor']
        self.total_cost = 0.0

    def run(self, user_input: str) -> str:
        start_time = time.time()
        self.total_cost = 0.0
        state = {'user_input': user_input, 'analysis': '', 'route': '', 'execution_result': '', 'critique': '', 'final_response': '', 'iteration': 0, 'is_finished': False}
        print('[Orchestrator] Start: ' + user_input[:50] + '...')
        while not state['is_finished'] and state['iteration'] < self.max_iterations:
            state['iteration'] += 1
            print('[Orchestrator] Iteration ' + str(state['iteration']) + '/' + str(self.max_iterations))
            state = self._analyze(state)
            state = self._route(state)
            state = self._execute(state)
            state = self._critique(state)
            if any(w in state['critique'].lower() for w in ['да', 'yes', 'ok', 'good', 'достаточно', 'отлично']):
                state['is_finished'] = True
                state = self._finish(state)
            elif state['iteration'] >= self.max_iterations:
                state['is_finished'] = True
                state['final_response'] = 'Max iterations. Result: ' + str(state['execution_result'])
                print('  -> Max iterations reached.')
        
        duration = time.time() - start_time
        success = state['is_finished'] and 'Max iterations' not in state['final_response']
        logger.log_request(
            user_input=state['user_input'],
            route=state['route'],
            execution_result=state['execution_result'],
            iterations=state['iteration'],
            duration=duration,
            cost=self.total_cost,
            success=success
        )
        print(f"[Orchestrator] Завершено за {duration:.2f}с, итераций: {state['iteration']}, стоимость: {self.total_cost:.4f} руб")
        return state['final_response']

    def _analyze(self, state):
        prompt = "Анализ запроса: '" + state['user_input'] + "'. Инструменты: " + self.tools_desc
        if state['iteration'] > 1: prompt += ". Критика: " + state['critique']
        state['analysis'], cost = self.llm.ask(prompt)
        self.total_cost += cost
        print("  -> Анализ: " + state['analysis'][:60] + "...")
        return state

    def _route(self, state):
        user_input_lower = state['user_input'].lower()
        if any(word in user_input_lower for word in ['найди', 'поиск', 'search', 'internet', 'интернет', 'кто такой', 'что такое', 'информация о']):
            state['route'] = 'web_search'
        elif any(word in user_input_lower for word in ['сохрани', 'файл', 'запиши', 'документ', 'save', 'file', 'write']):
            state['route'] = 'file_writer'
        elif any(word in user_input_lower for word in ['выполни', 'код', 'calculate', 'execute', 'посчитай', 'запусти']):
            state['route'] = 'code_executor'
        else:
            prompt = "Выбери строго одно: 'answer' или один из: " + ", ".join(self.tool_names) + ". Ответь только одним словом."
            route_raw, cost = self.llm.ask(prompt)
            self.total_cost += cost
            route_raw = route_raw.strip().lower().replace("'", "").replace('"', '')
            state['route'] = route_raw if route_raw in self.tool_names else 'answer'
        print("  -> Маршрут: " + state['route'])
        return state

    def _execute(self, state):
        if state['route'] == 'answer':
            state['execution_result'], cost = self.llm.ask("Краткий ответ по сути на: '" + state['user_input'] + "'. Анализ: " + state['analysis'])
            self.total_cost += cost
        else:
            tool = state['route']
            if tool == 'web_search':
                prompt = "Extract the main topic from this request and create a precise English search query (2-4 words). Request: '" + state['user_input'] + "'. Return ONLY the query, nothing else."
                search_query, cost = self.llm.ask(prompt)
                self.total_cost += cost
                search_query = search_query.strip().strip('"').strip("'")
                args = {'query': search_query}
            elif tool == 'code_executor':
                prompt = "Generate Python code for: '" + state['user_input'] + "'. Return ONLY the code, no explanations."
                code, cost = self.llm.ask(prompt)
                self.total_cost += cost
                code = code.strip()
                if code.startswith('```'):
                    code = '\n'.join(code.split('\n')[1:])
                if code.endswith('```'):
                    code = code[:-3]
                args = {'code': code}
            elif tool == 'file_writer':
                prompt = "Generate content to save for: '" + state['user_input'] + "'."
                content, cost = self.llm.ask(prompt)
                self.total_cost += cost
                args = {'file_path': 'agent_result.txt', 'content': content, 'mode': 'w'}
            else:
                args = {'query': state['user_input']}
            
            res = tool_registry.execute(tool, **args)
            state['execution_result'] = ('OK: ' + str(res['result'])) if res['success'] else ('Error: ' + str(res['error']))
        print("  -> Выполнение: " + state['execution_result'][:60] + "...")
        return state

    def _critique(self, state):
        prompt = """Ты - критик. Оцени, решает ли результат задачу пользователя.
Запрос: '{user_input}'
Результат: '{execution_result}'
Правила: если результат содержит релевантную информацию и решает задачу — ответь 'Да'. Только если полностью нерелевантен или содержит ошибку — ответь 'Нет'. Ответь одним словом: Да или Нет""".format(user_input=state['user_input'], execution_result=state['execution_result'][:500])
        state['critique'], cost = self.llm.ask(prompt)
        self.total_cost += cost
        print("  -> Критика: " + state['critique'][:60] + "...")
        return state

    def _finish(self, state):
        state['final_response'], cost = self.llm.ask("Итоговый краткий ответ пользователю ТОЛЬКО по сути: " + state['execution_result'])
        self.total_cost += cost
        print("  -> Завершение: ответ сформирован.")
        return state
