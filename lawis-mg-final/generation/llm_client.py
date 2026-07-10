"""LLM Client — OpenAI, Gemini ou OpenRouter selon LLM_PROVIDER dans .env.

Chaque fournisseur peut définir une liste de modèles (MODEL principal + *_MODELS de
secours). En cas d'erreur récupérable (429/402/timeout/5xx), on bascule
automatiquement sur le modèle suivant — utile pour les modèles gratuits
d'OpenRouter, fréquemment saturés.

Deux modes : `generate()` (réponse complète) et `generate_stream()` (flux de
tokens pour l'affichage progressif). Le fallback ne s'applique au streaming
qu'avant l'émission du premier token — une fois le flux commencé, on ne peut
plus rebasculer sans casser l'affichage côté client.
"""
import json
from collections.abc import Iterator
import requests
from loguru import logger
from core.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Statuts pour lesquels réessayer avec le modèle suivant a du sens.
# 401 (clé invalide) est fatal : changer de modèle n'y changera rien.
RETRYABLE_STATUS = {402, 408, 409, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """Erreur LLM enrichie d'un drapeau `retryable` pour piloter le fallback."""
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


def _raise_http_error(e: requests.exceptions.HTTPError, provider: str):
    status = e.response.status_code if e.response is not None else None
    body = e.response.text if e.response is not None else str(e)
    if status == 401:
        raise LLMError(f"Clé API {provider} invalide.", retryable=False)
    if status == 402:
        raise LLMError(f"Crédits {provider} insuffisants.", retryable=True)
    if status == 429:
        raise LLMError(f"Limite de requêtes {provider} atteinte. Réessayez dans un instant.", retryable=True)
    raise LLMError(f"Erreur {provider} {status} : {body[:300]}", retryable=status in RETRYABLE_STATUS)


def _generate_openai(system_prompt: str, user_message: str, model: str) -> str:
    if not settings.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY manquante dans .env", retryable=False)
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    logger.info(f"OpenAI → {model}")
    try:
        resp = requests.post(OPENAI_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.info(f"Réponse reçue ({len(content)} chars)")
        return content
    except requests.exceptions.Timeout:
        raise LLMError("Timeout OpenAI — réessayez.", retryable=True)
    except requests.exceptions.HTTPError as e:
        _raise_http_error(e, "OpenAI")


def _generate_gemini(system_prompt: str, user_message: str, model: str) -> str:
    if not settings.GEMINI_API_KEY:
        raise LLMError("GEMINI_API_KEY manquante dans .env", retryable=False)
    url = GEMINI_URL_TMPL.format(model=model)
    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": settings.LLM_TEMPERATURE, "maxOutputTokens": settings.LLM_MAX_TOKENS},
    }
    logger.info(f"Gemini → {model}")
    try:
        resp = requests.post(url, params={"key": settings.GEMINI_API_KEY}, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        logger.info(f"Réponse reçue ({len(content)} chars)")
        return content
    except requests.exceptions.Timeout:
        raise LLMError("Timeout Gemini — réessayez.", retryable=True)
    except requests.exceptions.HTTPError as e:
        _raise_http_error(e, "Gemini")


def _generate_openrouter(system_prompt: str, user_message: str, model: str) -> str:
    if not settings.OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY manquante dans .env", retryable=False)
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zenithsoft.ma",
        "X-Title": "LexIA Maroc",
    }
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
    }
    logger.info(f"OpenRouter → {model}")
    try:
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        logger.info(f"Réponse reçue ({len(content)} chars)")
        return content
    except requests.exceptions.Timeout:
        raise LLMError("Timeout OpenRouter — réessayez.", retryable=True)
    except requests.exceptions.HTTPError as e:
        _raise_http_error(e, "OpenRouter")


_PROVIDERS = {
    "openai": (_generate_openai, lambda: settings.openai_models_list),
    "gemini": (_generate_gemini, lambda: settings.gemini_models_list),
    "openrouter": (_generate_openrouter, lambda: settings.openrouter_models_list),
}


def generate(system_prompt: str, user_message: str) -> str:
    provider = settings.LLM_PROVIDER.lower()
    entry = _PROVIDERS.get(provider)
    if not entry:
        raise ValueError(f"LLM_PROVIDER invalide : {provider} (attendu : openai, gemini, openrouter)")
    fn, models_fn = entry
    models = models_fn()
    last_error: Exception | None = None
    for i, model in enumerate(models):
        try:
            return fn(system_prompt, user_message, model)
        except LLMError as e:
            last_error = e
            if not e.retryable:
                logger.error(f"Erreur LLM fatale ({provider}/{model}): {e}")
                raise
            remaining = len(models) - i - 1
            if remaining:
                logger.warning(f"Modèle {provider}/{model} indisponible ({e}) — bascule sur le suivant ({remaining} restant(s)).")
            else:
                logger.error(f"Erreur LLM ({provider}/{model}): {e} — aucun modèle de secours restant.")
        except Exception as e:
            last_error = e
            logger.error(f"Erreur LLM inattendue ({provider}/{model}): {e}")
            raise
    raise last_error if last_error else RuntimeError("Aucun modèle LLM disponible.")


# ─────────────────────────── Streaming ───────────────────────────

def _stream_openai_compatible(url: str, headers: dict, model: str, system_prompt: str,
                              user_message: str, provider: str) -> Iterator[str]:
    """Flux SSE pour les API compatibles OpenAI (OpenAI + OpenRouter)."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
        "temperature": settings.LLM_TEMPERATURE,
        "max_tokens": settings.LLM_MAX_TOKENS,
        "stream": True,
    }
    logger.info(f"{provider} (stream) → {model}")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=(10, 120), stream=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise LLMError(f"Timeout {provider} — réessayez.", retryable=True)
    except requests.exceptions.HTTPError as e:
        _raise_http_error(e, provider)
    for raw in resp.iter_lines():
        if not raw:
            continue
        line = raw.decode("utf-8").strip()
        if not line.startswith("data:"):
            continue
        data = line[len("data:"):].strip()
        if data == "[DONE]":
            break
        try:
            delta = json.loads(data)["choices"][0]["delta"].get("content")
        except (json.JSONDecodeError, KeyError, IndexError):
            continue
        if delta:
            yield delta


def _stream_openai(system_prompt: str, user_message: str, model: str) -> Iterator[str]:
    if not settings.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY manquante dans .env", retryable=False)
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
    return _stream_openai_compatible(OPENAI_URL, headers, model, system_prompt, user_message, "OpenAI")


def _stream_openrouter(system_prompt: str, user_message: str, model: str) -> Iterator[str]:
    if not settings.OPENROUTER_API_KEY:
        raise LLMError("OPENROUTER_API_KEY manquante dans .env", retryable=False)
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://zenithsoft.ma",
        "X-Title": "LexIA Maroc",
    }
    return _stream_openai_compatible(OPENROUTER_URL, headers, model, system_prompt, user_message, "OpenRouter")


def _stream_gemini(system_prompt: str, user_message: str, model: str) -> Iterator[str]:
    """Gemini : dégradation en un seul bloc (pas de vrai streaming SSE ici)."""
    yield _generate_gemini(system_prompt, user_message, model)


_STREAM_PROVIDERS = {
    "openai": (_stream_openai, lambda: settings.openai_models_list),
    "gemini": (_stream_gemini, lambda: settings.gemini_models_list),
    "openrouter": (_stream_openrouter, lambda: settings.openrouter_models_list),
}


def generate_stream(system_prompt: str, user_message: str) -> Iterator[str]:
    """
    Génère la réponse en flux de tokens. Bascule sur le modèle de secours
    uniquement si l'erreur survient AVANT le premier token (sinon on ne peut
    plus rebasculer sans casser l'affichage déjà commencé côté client).
    """
    provider = settings.LLM_PROVIDER.lower()
    entry = _STREAM_PROVIDERS.get(provider)
    if not entry:
        raise ValueError(f"LLM_PROVIDER invalide : {provider} (attendu : openai, gemini, openrouter)")
    stream_fn, models_fn = entry
    models = models_fn()
    last_error: Exception | None = None
    for i, model in enumerate(models):
        try:
            gen = stream_fn(system_prompt, user_message, model)
            first = next(gen)  # déclenche l'ouverture du flux — peut lever avant tout token
        except StopIteration:
            return  # flux vide mais sans erreur
        except LLMError as e:
            last_error = e
            if not e.retryable:
                logger.error(f"Erreur LLM stream fatale ({provider}/{model}): {e}")
                raise
            remaining = len(models) - i - 1
            if remaining:
                logger.warning(f"Modèle {provider}/{model} indisponible ({e}) — bascule stream sur le suivant ({remaining} restant(s)).")
            else:
                logger.error(f"Erreur LLM stream ({provider}/{model}): {e} — aucun modèle de secours restant.")
            continue
        # Premier token obtenu : on est engagé sur ce modèle.
        yield first
        yield from gen
        return
    raise last_error if last_error else RuntimeError("Aucun modèle LLM disponible.")
