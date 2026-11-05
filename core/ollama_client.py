"""
Local Ollama API client for air-gapped LLM execution.

Strictly communicates with 127.0.0.1. No external network routing is permitted.
"""

import json
import re
import requests

from config.settings import OLLAMA_HOST, OLLAMA_MODEL, REQUEST_TIMEOUT


class OllamaConnectionError(ConnectionError):
    """Raised when the local Ollama instance cannot be reached."""


class OllamaExecutionError(RuntimeError):
    """Raised when Ollama returns an invalid or unparseable response."""


def call_local_ollama(
    prompt: str,
    system_prompt: str,
    model: str = OLLAMA_MODEL,
    temperature: float = 0.0,
) -> dict:
    """
    Execute a prompt against the local Ollama instance with JSON format enforcement.

    Args:
        prompt: The user prompt to send to the model.
        system_prompt: The system instruction for the agent.
        model: Ollama model identifier (default: llama3.1:latest).
        temperature: Sampling temperature (0.0 = deterministic).

    Returns:
        Parsed JSON object from the model response.

    Raises:
        OllamaConnectionError: If Ollama is not reachable on localhost.
        OllamaExecutionError: If the response cannot be parsed as JSON.
    """
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()
        raw_output = res_json.get("response", "").strip()

        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Fallback: attempt to extract a JSON object from the text
            match = re.search(r"\{.*\}", raw_output, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise OllamaExecutionError(
                f"Failed to parse valid JSON from Ollama response: {raw_output[:200]}..."
            )

    except requests.exceptions.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Cannot connect to local Ollama instance at {OLLAMA_HOST}. "
            "Verify Ollama is running locally ('ollama serve') and accessible on localhost. "
            "Air-gapped operation forbids external network routing."
        ) from exc
    except OllamaExecutionError:
        raise
    except Exception as exc:
        raise OllamaExecutionError(f"Ollama execution failed: {str(exc)}") from exc
