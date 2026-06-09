import subprocess
import json
import sys
import time
sys.path.insert(0, '/home/user/nexus-builder')
from config import POLZA_API_URL, POLZA_API_KEY, POLZA_MODEL, MAX_TOKENS, TEMPERATURE, TIMEOUT

class LLMClient:
    def __init__(self):
        self.url = POLZA_API_URL
        self.api_key = POLZA_API_KEY
        self.model = POLZA_MODEL
    
    def ask(self, prompt, system_prompt=None):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS
        }
        
        # Записываем JSON во временный файл (избегаем проблем с экранированием)
        tmp_file = "/tmp/llm_request.json"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        
        try:
            start = time.time()
            # Используем shell=True и @file для передачи JSON
            cmd = f'curl -k -s -X POST "{self.url}" -H "Content-Type: application/json" -H "Authorization: Bearer {self.api_key}" -d @{tmp_file} --max-time {TIMEOUT}'
            result = subprocess.run(
                cmd, 
                shell=True, 
                executable="/bin/bash",
                capture_output=True, 
                text=True, 
                timeout=TIMEOUT+10
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
                return f"Error: {response['error']}"
            else:
                return f"Error: unexpected - {result.stdout[:200]}", 0.0
        except Exception as e:
            return f"Error: {e}", 0.0
        finally:
            # Удаляем временный файл
            try:
                import os
                os.remove(tmp_file)
            except:
                pass
