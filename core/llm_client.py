import subprocess
import json
import sys
import time
import tempfile
import os
from config import POLZA_API_URL, POLZA_API_KEY, POLZA_MODEL, MAX_TOKENS, TEMPERATURE, TIMEOUT


class LLMClient:
    def __init__(self):
        self.url = POLZA_API_URL
        self.api_key = POLZA_API_KEY
        self.model = POLZA_MODEL

    def ask(self, prompt: str, system_prompt: str = None, max_tokens: int = None) -> tuple[str, float]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        data = {
            "model": self.model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": max_tokens or MAX_TOKENS,
        }

        # Используем NamedTemporaryFile чтобы избежать гонки при параллельных запросах
        tmp_fd, tmp_file = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(tmp_fd, "w") as f:
                json.dump(data, f)

            start = time.time()
            # Передаём аргументы списком — shell=False, инъекция через url/api_key невозможна
            cmd = [
                "curl", "-k", "-s", "-X", "POST", self.url,
                "-H", "Content-Type: application/json",
                "-H", f"Authorization: Bearer {self.api_key}",
                "-d", f"@{tmp_file}",
                "--max-time", str(TIMEOUT),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT + 10,
            )
            elapsed = time.time() - start

            if result.returncode != 0:
                print(f"DEBUG curl stderr: {result.stderr[:300]}")
                return f"Error: curl failed (code {result.returncode})", 0.0

            if not result.stdout.strip():
                return "Error: empty response from curl", 0.0

            response = json.loads(result.stdout)

            if "choices" in response:
                content = response["choices"][0]["message"]["content"]
                cost = response.get("usage", {}).get("cost_rub", 0)
                print(f"OK: {elapsed:.2f}s | {cost:.6f}rub")
                return content, cost
            elif "error" in response:
                return f"Error: {response['error']}", 0.0
            else:
                return f"Error: unexpected - {result.stdout[:200]}", 0.0

        except json.JSONDecodeError as e:
            return f"Error: invalid JSON response - {e}", 0.0
        except Exception as e:
            return f"Error: {e}", 0.0
        finally:
            try:
                os.remove(tmp_file)
            except OSError:
                pass
