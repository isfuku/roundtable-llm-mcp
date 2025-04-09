import os
import httpx


class LLMClient:
    """Manages communication with the LLM provider."""

    def __init__(self) -> None:
        self.api_key: str = os.environ["LLM_API_KEY"]

    def get_response(self, messages: list[dict[str, str]]) -> str:
        url = "https://api.mistral.ai/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "Host": "api.mistral.ai",
            "user-agent": "mistral-client-python/1.6.0",
        }
        payload = {
            "messages": messages,
            "model": "mistral-large-latest",
        }
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            tool_calls = data["choices"][0]["message"].get("tool_calls")
            if tool_calls:
                tool_call = tool_calls[0]["function"]
                tool_call["tool"] = tool_call.pop("name")
                return str(tool_call)
            return data["choices"][0]["message"]["content"]
