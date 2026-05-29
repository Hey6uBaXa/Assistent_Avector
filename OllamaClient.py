import threading
from ollama import Client
from libs.config import LM
from tools import tool_specs, available_functions
from utils.logger import log_info, log_error
from tts_engine import TTS

class OllamaClient:
    def __init__(self):
        key = "ollama_remote" if LM["remote_ollama"] else "ollama_local"
        config = LM[key]

        self.model_name = config["model_name"]
        self.system_role = config["system_role"]
        self.temperature = config["temperature"]
        self.max_tokens = config["max_tokens"]
        self.messages = []
        self.tools = tool_specs

        self.client = Client(host=config["api_url"])  # локальный или удалённый Ollama

    def execute_tool_async(self, func, args: dict):
        """Запуск функции в отдельном потоке."""
        def target():
            try:
                output = func(**args)
                log_info(f"Tool '{func.__name__}' выполнен: {output}")
            except Exception as e:
                log_error(f"Ошибка в функции '{func.__name__}': {e}")
        t = threading.Thread(target=target)
        t.start()

    def ask(self, prompt: str) -> str:
        log_info(f"Ollama request: {prompt}")
        self.messages = [
            {"role": "system", "content": self.system_role},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.client.chat(
                model=self.model_name,
                messages=self.messages,
                tools=self.tools,
                options={
                    "temperature": self.temperature,
                    "num_predict": 512,
                    "num_ctx": 1024,
                    "think": False,
                    "stream": False
                }
            )

            reply_text = response["message"]["content"]
            log_info(f"Ollama reply: {reply_text}")

            # 🔹 Параллельно выполняем tool_calls
            if "tool_calls" in response["message"]:
                for tool_call in response["message"]["tool_calls"]:
                    name = tool_call["function"]["name"]
                    args = tool_call["function"].get("arguments", {})
                    func = available_functions.get(name)
                    if func:
                        self.execute_tool_async(func, args)
                    else:
                        log_error(f"Функция '{name}' не найдена")

            # # 🔹 Всегда озвучиваем текст
            # if reply_text.strip():
            #     tts_thread = threading.Thread(target=tts.speak, args=(reply_text,))
            #     tts_thread.start()

            return reply_text

        except Exception as e:
            log_error(f"Ошибка Ollama: {e}")
            return ""

LLM_Client = OllamaClient()

if __name__ == "__main__":
    TTS.speak_streaming(LLM_Client.ask("сделай шаг вперёд"))