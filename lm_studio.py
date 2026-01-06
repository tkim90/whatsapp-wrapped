"""LM Studio API client for embeddings and chat completions."""

import requests
from typing import Any


class LMStudioClient:
    """Client for interacting with LM Studio's OpenAI-compatible API."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234/v1",
        embedding_model: str = "text-embedding-nomic-embed-text-v1.5",
        chat_model: str = "openai/gpt-oss-20b",
        timeout: int = 120
    ):
        self.base_url = base_url.rstrip('/')
        self.embedding_model = embedding_model
        self.chat_model = chat_model
        self.timeout = timeout

    def _post(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        """Make a POST request to LM Studio."""
        url = f"{self.base_url}/{endpoint}"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for a single text."""
        data = {
            "model": self.embedding_model,
            "input": text
        }

        result = self._post("embeddings", data)
        return result["data"][0]["embedding"]

    def get_embeddings_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Get embedding vectors for multiple texts in batches."""
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            data = {
                "model": self.embedding_model,
                "input": batch
            }

            result = self._post("embeddings", data)
            # Sort by index to maintain order
            sorted_data = sorted(result["data"], key=lambda x: x["index"])
            embeddings = [item["embedding"] for item in sorted_data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = -1,
        stream: bool = False
    ) -> str:
        """Generate a chat completion."""
        data = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream
        }

        result = self._post("chat/completions", data)
        return result["choices"][0]["message"]["content"]

    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = -1
    ) -> str:
        """Simple generation with optional system prompt."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat_completion(messages, temperature, max_tokens)

    def is_available(self) -> bool:
        """Check if LM Studio server is available."""
        try:
            response = requests.get(f"{self.base_url}/models", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False


# Default client instance
_client: LMStudioClient | None = None


def get_client() -> LMStudioClient:
    """Get or create the default LM Studio client."""
    global _client
    if _client is None:
        _client = LMStudioClient()
    return _client


if __name__ == '__main__':
    client = LMStudioClient()

    if client.is_available():
        print("LM Studio is available!")

        # Test embedding
        print("\nTesting embedding...")
        embedding = client.get_embedding("Hello, world!")
        print(f"Embedding dimension: {len(embedding)}")

        # Test chat completion
        print("\nTesting chat completion...")
        response = client.generate(
            "Say hello in a creative way.",
            system_prompt="You are a friendly assistant."
        )
        print(f"Response: {response}")
    else:
        print("LM Studio is not available. Make sure it's running at http://127.0.0.1:1234")
