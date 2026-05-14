"""
LLM Client - Unified interface for OpenRouter and OpenAI
"""
import os
import json
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

# Global for tracking
_last_model_used = None
_fallback_triggered = False

# Runtime API key storage (set by user via UI)
RUNTIME_API_KEY = None


def set_api_key(key):
    """Set API key at runtime (from UI input)"""
    global RUNTIME_API_KEY
    RUNTIME_API_KEY = key
    print(f"[LLM] API key updated via UI")


def get_api_key():
    """Get API key - prefer runtime over env"""
    if RUNTIME_API_KEY:
        return RUNTIME_API_KEY
    return os.getenv("OPENROUTER_API_KEY")


def call_llm(prompt, system_prompt=None, json_mode=False):
    """
    Unified LLM call function with OpenRouter primary and OpenAI fallback.

    Args:
        prompt: The user prompt
        system_prompt: Optional system prompt
        json_mode: If True, expect JSON response

    Returns:
        str or dict: Text content or parsed JSON dict
    """
    global _last_model_used, _fallback_triggered

    start_time = time.time()
    headers = {
        "Content-Type": "application/json"
    }

    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Build request payload
    payload = {
        "model": "arcee-ai/trinity-large-preview",
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 1024
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    # Try OpenRouter first
    if openrouter_key:
        try:
            headers["Authorization"] = f"Bearer {openrouter_key}"
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=8
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                _last_model_used = "arcee-ai/trinity-large-preview"
                _fallback_triggered = False

                latency_ms = int((time.time() - start_time) * 1000)
                tokens_used = result.get("usage", {}).get("total_tokens", 0)
                print(f"[LLM] OpenRouter | model={_last_model_used} | tokens={tokens_used} | latency={latency_ms}ms")

                if json_mode:
                    return _parse_json_response(content)
                return content
            else:
                print(f"[LLM] OpenRouter failed: {response.status_code} - trying fallback")

        except requests.exceptions.Timeout:
            print("[LLM] OpenRouter timeout - trying fallback")
        except Exception as e:
            print(f"[LLM] OpenRouter error: {e} - trying fallback")

    # Fallback to OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise Exception("No LLM API keys available")

    try:
        headers["Authorization"] = f"Bearer {openai_key}"
        payload["model"] = "gpt-4o-mini"

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            _last_model_used = "openai/gpt-4o-mini"
            _fallback_triggered = True

            latency_ms = int((time.time() - start_time) * 1000)
            tokens_used = result.get("usage", {}).get("total_tokens", 0)
            print(f"[LLM] OpenAI Fallback | model={_last_model_used} | tokens={tokens_used} | latency={latency_ms}ms")

            if json_mode:
                return _parse_json_response(content)
            return content
        else:
            raise Exception(f"OpenAI API failed: {response.status_code}")

    except Exception as e:
        raise Exception(f"All LLM providers failed: {e}")


def _parse_json_response(content):
    """Parse JSON from LLM response, handling common issues."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from text using regex
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except:
                pass
        return {"error": "Failed to parse JSON", "raw": content}