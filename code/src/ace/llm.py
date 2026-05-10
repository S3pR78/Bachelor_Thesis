"""
==============================================================================
llm.py
==============================================================================

This file contains the LLM class for the project.

"""
import time
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from ace.logger import log_llm_call, log_problematic_request

try:
    import openai
except ImportError:
    openai = None


LOCAL_PROVIDERS = {"huggingface", "hf", "local"}
DEFAULT_MODEL_CONFIG_PATH = "code/config/model_config.json"


@dataclass
class AceLLMClient:
    """Prepared ACE LLM runtime for either OpenAI chat or local HF generation."""

    provider: str
    model_id: str
    model_config: dict[str, Any]
    client: Any | None = None
    tokenizer: Any | None = None
    model: Any | None = None


@dataclass
class AceLlmSessionCache:
    """Process-local cache for ACE model runtimes keyed by config path + key."""

    model_config_path: str = DEFAULT_MODEL_CONFIG_PATH
    clients: dict[str, AceLLMClient] | None = None

    def __post_init__(self) -> None:
        if self.clients is None:
            self.clients = {}

    def cache_key(self, model_key: str, model_config_path: str | None = None) -> str:
        config_path = Path(model_config_path or self.model_config_path).resolve()
        return f"{config_path}::{model_key.strip().lower()}"

    def get(self, model_key: str, model_config_path: str | None = None) -> AceLLMClient:
        path = model_config_path or self.model_config_path
        return resolve_ace_llm_client(
            path,
            model_key,
            cache=self.clients,
        )


PROCESS_ACE_LLM_CACHE = AceLlmSessionCache()


def normalize_provider(provider: str | None) -> str:
    return str(provider or "").strip().lower()


def is_local_provider(provider: str | None) -> bool:
    return normalize_provider(provider) in LOCAL_PROVIDERS


def get_model_id(model_config: dict[str, Any], *, model_key: str | None = None) -> str:
    model_id = model_config.get("model_id")
    if not model_id:
        suffix = f" for model_key={model_key!r}" if model_key else ""
        raise ValueError(f"Missing model_id{suffix}.")
    return str(model_id)


def get_api_env_var(model_config: dict[str, Any]) -> str:
    api_config = model_config.get("api", {})
    return (
        api_config.get("api_key_env")
        or api_config.get("env_var_name")
        or "OPENAI_API_KEY"
    )


def get_max_tokens_from_model_config(
    model_config: dict[str, Any],
    *,
    cli_max_tokens: int | None = None,
    default: int = 1024,
) -> int:
    if cli_max_tokens is not None:
        return cli_max_tokens

    generation = model_config.get("generation", {})
    value = (
        generation.get("max_output_tokens")
        or generation.get("max_new_tokens")
        or model_config.get("max_tokens")
        or default
    )
    return int(value)


def get_process_ace_llm_cache(
    model_config_path: str = DEFAULT_MODEL_CONFIG_PATH,
) -> AceLlmSessionCache:
    if str(Path(model_config_path).resolve()) == str(
        Path(PROCESS_ACE_LLM_CACHE.model_config_path).resolve()
    ):
        return PROCESS_ACE_LLM_CACHE

    return AceLlmSessionCache(model_config_path=model_config_path)


def _load_model_config_for_key(
    model_key: str,
    model_config_path: str,
) -> dict[str, Any]:
    from src.utils.config_loader import load_json_config, get_model_entry

    full_config = load_json_config(model_config_path)
    return get_model_entry(full_config, model_key)


def _fallback_cache_key(
    model_config: dict[str, Any],
    *,
    model_key: str | None = None,
    model_config_path: str | None = None,
) -> str:
    if model_key and model_config_path:
        return f"{Path(model_config_path).resolve()}::{model_key.strip().lower()}"

    provider = normalize_provider(model_config.get("provider"))
    model_id = get_model_id(model_config, model_key=model_key)
    paths = model_config.get("paths", {})
    model_path = model_config.get("model_path") or paths.get("model_path") or paths.get("finetuned_path")
    adapter_path = model_config.get("adapter_path") or paths.get("adapter_path")
    variant = model_config.get("variant", "")
    return f"{provider}:{model_id}:{variant}:{model_path}:{adapter_path}"


def prepare_ace_llm_client(
    model_config: dict[str, Any] | str | None = None,
    model_config_path: str | None = None,
    *,
    model_key: str | None = None,
    cache: dict[str, AceLLMClient] | None = None,
) -> AceLLMClient:
    """Prepare an ACE LLM client from a model_config entry.

    OpenAI remains a lightweight chat client. HuggingFace/local providers use
    the repository's model_loader so Reflector, Curator, Refiner, and future
    ACE agents resolve models the same way the evaluation stack does.
    """
    if isinstance(model_config, str):
        model_key = model_config
        model_config = None

    if model_config is None:
        if not model_key:
            raise ValueError("Either model_config or model_key must be provided.")
        model_config_path = model_config_path or DEFAULT_MODEL_CONFIG_PATH
        model_config = _load_model_config_for_key(model_key, model_config_path)

    provider = normalize_provider(model_config.get("provider"))
    model_id = get_model_id(model_config, model_key=model_key)
    if cache is None:
        cache = PROCESS_ACE_LLM_CACHE.clients
    cache_key = _fallback_cache_key(
        model_config,
        model_key=model_key,
        model_config_path=model_config_path,
    )

    if cache is not None and cache_key in cache:
        if is_local_provider(provider):
            print(f"Reusing cached local ACE model for key={model_key or model_id}")
        return cache[cache_key]

    if provider == "openai":
        from src.core.openai_provider import create_openai_client

        prepared = AceLLMClient(
            provider=provider,
            model_id=model_id,
            model_config=model_config,
            client=create_openai_client(env_var_name=get_api_env_var(model_config)),
        )
    elif is_local_provider(provider):
        from src.core.model_loader import load_model_and_tokenizer

        print(f"Loading local ACE model for key={model_key or model_id}")
        tokenizer, model = load_model_and_tokenizer(model_config)
        prepared = AceLLMClient(
            provider=provider,
            model_id=model_id,
            model_config=model_config,
            tokenizer=tokenizer,
            model=model,
        )
    else:
        raise ValueError(
            f"Unsupported ACE model provider {provider!r} for model_key={model_key!r}. "
            "Supported configured providers are 'openai' and 'huggingface'."
        )

    if cache is not None:
        cache[cache_key] = prepared

    return prepared


def resolve_ace_llm_client(
    config_path: str,
    model_key: str,
    *,
    cache: dict[str, AceLLMClient] | None = None,
) -> AceLLMClient:
    """Load model_config and prepare one ACE LLM runtime by key."""
    model_config = _load_model_config_for_key(model_key, config_path)
    return prepare_ace_llm_client(
        model_config,
        model_config_path=config_path,
        model_key=model_key,
        cache=cache,
    )


def ace_client_to_inference_session(
    client: AceLLMClient,
    *,
    model_key: str,
) -> dict[str, Any]:
    """Expose an ACE runtime through the evaluation inference-session shape."""
    if client.provider == "openai":
        return {
            "provider": "openai",
            "model_name": model_key,
            "model_config": client.model_config,
            "client": client.client,
            "env_var_name": get_api_env_var(client.model_config),
        }

    if is_local_provider(client.provider):
        return {
            "provider": client.provider,
            "model_name": model_key,
            "model_config": client.model_config,
            "tokenizer": client.tokenizer,
            "model": client.model,
        }

    raise ValueError(f"Unsupported ACE client provider for inference: {client.provider!r}")


def _unwrap_prepared_client(client, api_provider: str, model: str) -> tuple[Any, str, str, dict[str, Any] | None]:
    if isinstance(client, AceLLMClient):
        return client, client.provider, client.model_id, client.model_config

    return client, normalize_provider(api_provider), model, None


def _get_openai_usage_value(response: Any, name: str) -> int | None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(name)
    return getattr(usage, name, None)


def _generate_local_response(prepared: AceLLMClient, prompt: str, max_tokens: int) -> str:
    if prepared.model is None or prepared.tokenizer is None:
        raise ValueError("Local ACE LLM client is missing model/tokenizer.")

    from src.core.model_loader import generate_raw_response

    generation = prepared.model_config.get("generation", {})
    return generate_raw_response(
        model=prepared.model,
        tokenizer=prepared.tokenizer,
        prompt=prompt,
        max_new_tokens=max_tokens,
        do_sample=generation.get("do_sample", False),
        temperature=generation.get("temperature", 0.0),
    )


def timed_llm_call(client, api_provider, model, prompt, role, call_id, max_tokens=4096, log_dir=None,
                   sleep_seconds=15, retries_on_timeout=1000, attempt=1, use_json_mode=False):
    """
    Make a timed LLM call with error handling and retry logic.
    
    EMPTY RESPONSE HANDLING STRATEGY:
    - Training calls (call_id starts with 'train_'): Skip the entire training sample
    - Test calls (call_id starts with 'test_'): Mark as incorrect (return wrong answers)
    - All empty responses are logged to problematic_requests/ for SambaNova support analysis
    
    For test calls specifically: Returns "INCORRECT_DUE_TO_EMPTY_RESPONSE" repeated 4 times
    (comma-separated) to handle the 4-question format used in financial NER evaluation.
    
    Args:
        client: API client
        model: Model name to use
        prompt: Text prompt to send
        role: Role for logging (generator, reflector, curator)
        call_id: Unique identifier for this call (format: {train|test}_{role}_{details})
        max_tokens: Maximum tokens to generate
        log_dir: Directory for detailed logging
        sleep_seconds: Base sleep time between retries
        retries_on_timeout: Maximum number of retries for timeouts/rate limits/empty responses
        attempt: Current attempt number (for recursive calls)
        use_json_mode: Whether to use JSON mode for structured output
    
    Returns:
        tuple: (response_text, call_info_dict)
        
    Special return values for empty responses:
        - Training: ("INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, ...", call_info)
        - Testing: ("INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, ...", call_info)
    """
    start_time = time.time()
    prompt_time = time.time()
    api_params = {}
    
    print(f"[{role.upper()}] Starting call {call_id}...")
    
    # Check if we're using API key mixer for dynamic key rotation on retries
    using_key_mixer = False
    
    while True:
        try:
            # Get client
            active_client, resolved_provider, resolved_model, model_config = _unwrap_prepared_client(
                client,
                api_provider,
                model,
            )

            # Prepare API call parameters
            if is_local_provider(resolved_provider):
                api_params = {
                    "model": resolved_model,
                    "provider": resolved_provider,
                    "max_new_tokens": max_tokens,
                    "use_json_mode": use_json_mode,
                }

                call_start = time.time()
                response_content = _generate_local_response(
                    active_client,
                    prompt,
                    max_tokens=max_tokens,
                )
                call_end = time.time()
            else:
                if isinstance(active_client, AceLLMClient):
                    active_client = active_client.client

                if active_client is None:
                    raise ValueError(f"No chat client configured for provider {resolved_provider!r}.")

                if resolved_provider == "openai":
                    max_tokens_key = "max_completion_tokens"
                else:
                    max_tokens_key = "max_tokens"

                api_params = {
                    "model": resolved_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    max_tokens_key: max_tokens
                }
                
                # Add JSON mode if requested
                if use_json_mode:
                    api_params["response_format"] = {"type": "json_object"}
                call_start = time.time()
                response = active_client.chat.completions.create(**api_params)
                call_end = time.time()
                
                # Check if response is valid
                if not response or not response.choices or len(response.choices) == 0:
                    raise Exception("Empty response from API")
                
                response_content = response.choices[0].message.content
            
            if response_content is None:
                raise Exception("API returned None content")

            if not str(response_content).strip():
                raise Exception("Empty response from API")

            response_time = time.time()
            total_time = response_time - start_time
            
            call_info = {
                "role": role,
                "call_id": call_id,
                "model": resolved_model,
                "provider": resolved_provider,
                "prompt": prompt,
                "response": response_content,
                "prompt_time": prompt_time - start_time,
                "response_time": response_time - prompt_time,
                "total_time": total_time,
                "call_time": call_end - call_start,
                "prompt_length": len(prompt),
                "response_length": len(response_content),
                "prompt_num_tokens": None,
                "response_num_tokens": None,
            }

            if not is_local_provider(resolved_provider):
                call_info["prompt_num_tokens"] = _get_openai_usage_value(response, "prompt_tokens")
                call_info["response_num_tokens"] = _get_openai_usage_value(response, "completion_tokens")
            
            print(f"[{role.upper()}] Call {call_id} completed in {total_time:.2f}s")
            
            if log_dir:
                log_llm_call(log_dir, call_info)
            
            return response_content, call_info
            
        except Exception as e:
            # Check for both timeout and rate limit errors
            is_timeout = any(k in str(e).lower() for k in ["timeout", "timed out", "connection"])
            is_rate_limit = any(k in str(e).lower() for k in ["rate limit", "429", "rate_limit_exceeded"])
            is_empty_response = "empty response" in str(e).lower() or "api returned none content" in str(e).lower()
            
            # Check for server errors (500, 502, 503, etc.) that should be retried
            is_server_error = False
            if hasattr(e, 'response'):
                try:
                    status_code = getattr(e.response, 'status_code', None)
                    if status_code and status_code >= 500:
                        is_server_error = True
                        print(f"[{role.upper()}] Server error detected: HTTP {status_code}")
                except:
                    pass
            
            # Also check for 500 errors in the error message itself
            if any(k in str(e).lower() for k in ["500 internal server error", "internal server error", "502 bad gateway", "503 service unavailable"]):
                is_server_error = True
                print(f"[{role.upper()}] Server error detected in message: {str(e)[:100]}...")
            
            # Also check for specific OpenAI exceptions
            if openai is not None and hasattr(openai, 'RateLimitError') and isinstance(e, openai.RateLimitError):
                is_rate_limit = True
            
            # Check for OpenAI InternalServerError
            if openai is not None and hasattr(openai, 'InternalServerError') and isinstance(e, openai.InternalServerError):
                is_server_error = True
                print(f"[{role.upper()}] OpenAI InternalServerError detected")
            
            # Debug empty response issues
            if is_empty_response:
                print(f"\n🚨 DEBUG: Empty response detected for {call_id}")
                print(f"📝 Exception type: {type(e).__name__}")
                print(f"📝 Exception message: {str(e)}")
                print(f"📝 Using JSON mode: {use_json_mode}")
                print(f"📝 Model: {model}")
                print(f"📝 Prompt length: {len(prompt)}")
                print(f"📝 Prompt preview (first 500 chars):")
                print(f"    {prompt[:500]}...")
                print(f"📝 Full exception details: {repr(e)}")
                if hasattr(e, 'response'):
                    print(f"📝 Raw response object: {e.response}")
                    if hasattr(e.response, 'text'):
                        print(f"📝 Raw response text: {e.response.text}")
                    if hasattr(e.response, 'content'):
                        print(f"📝 Raw response content: {e.response.content}")
                print("-" * 60)
                
                # Log problematic requests for SambaNova support
                log_problematic_request(call_id, prompt, model, api_params, e, log_dir, using_key_mixer, 
                                       client if using_key_mixer else None)
            
            # For empty responses, we handle differently based on context
            if is_empty_response:
                # Log the problematic request for SambaNova support
                log_problematic_request(call_id, prompt, model, api_params, e, log_dir, using_key_mixer, 
                                       client if using_key_mixer else None)
                
                # Check if this is a training or test call to decide behavior
                if call_id.startswith('train_'):
                    # In training: Mark as incorrect answer (same as testing)
                    print(f"[{role.upper()}] 🚨 Empty response in training - marking as INCORRECT for {call_id}")
                    error_time = time.time()
                    call_info = {
                        "role": role,
                        "call_id": call_id,
                        "model": model,
                        "prompt": prompt,
                        "error": "TRAINING_INCORRECT: " + str(e),
                        "total_time": error_time - start_time,
                        "prompt_length": len(prompt),
                        "response_length": 0,
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
                        "datetime": datetime.now().isoformat(),
                        "training_marked_incorrect_due_to_empty_response": True
                    }
                    if log_dir:
                        log_llm_call(log_dir, call_info)
                    
                    # Return a response that will be marked as incorrect
                    # For the 4-question format, we return 4 wrong answers
                    incorrect_response = "INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE"
                    return incorrect_response, call_info
                
                elif call_id.startswith('test_'):
                    # In testing: Treat as incorrect answer
                    print(f"[{role.upper()}] 🚨 Empty response in testing - marking as INCORRECT for {call_id}")
                    error_time = time.time()
                    call_info = {
                        "role": role,
                        "call_id": call_id,
                        "model": model,
                        "prompt": prompt,
                        "error": "TEST_INCORRECT: " + str(e),
                        "total_time": error_time - start_time,
                        "prompt_length": len(prompt),
                        "response_length": 0,
                        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3],
                        "datetime": datetime.now().isoformat(),
                        "test_marked_incorrect_due_to_empty_response": True
                    }
                    if log_dir:
                        log_llm_call(log_dir, call_info)
                    
                    # Return a response that will be marked as incorrect
                    # For the 4-question format, we return 4 wrong answers
                    incorrect_response = "INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE, INCORRECT_DUE_TO_EMPTY_RESPONSE"
                    return incorrect_response, call_info
            
            # Retry logic for timeouts, rate limits, and server errors
            if (is_timeout or is_rate_limit or is_server_error) and attempt < retries_on_timeout:
                attempt += 1
                if is_rate_limit:
                    error_type = "rate limited"
                    base_sleep = sleep_seconds * 2
                elif is_server_error:
                    error_type = "server error (500+)"
                    base_sleep = sleep_seconds * 1.5  # Moderate delay for server errors
                elif is_empty_response:
                    error_type = "returned empty response"
                    base_sleep = sleep_seconds
                else:
                    error_type = "timed out"
                    base_sleep = sleep_seconds
                jitter = random.uniform(0.5, 1.5)  # Add jitter to avoid thundering herd
                sleep_time = base_sleep * jitter
                print(f"[{role.upper()}] Call {call_id} {error_type}, sleeping {sleep_time:.1f}s then retrying "
                      f"({attempt}/{retries_on_timeout})...")
                time.sleep(sleep_time)
                continue
            
            error_time = time.time()
            call_info = {
                "role": role,
                "call_id": call_id,
                "model": model,
                "prompt": prompt,
                "error": str(e),
                "total_time": error_time - start_time,
                "prompt_length": len(prompt),
                "attempt": attempt,
            }
            
            print(f"[{role.upper()}] Call {call_id} failed after {error_time - start_time:.2f}s: {e}")
            
            if log_dir:
                log_llm_call(log_dir, call_info)
            
            raise e
