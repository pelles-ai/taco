"""Unified LLM wrapper supporting Anthropic Claude and OpenAI.

Usage:
    llm = LLMProvider()
    result = await llm.generate_json(system_prompt, user_prompt, EstimateV1)

``generate_json`` returns a JSON-ready dict that has been validated against
the Pydantic model you pass in. On Anthropic the model also constrains the
response through structured outputs (``output_config.format``).

Every failure is raised as ``LLMError``. Its message is short and safe to
send back to A2A callers; provider details (status codes, response bodies,
request IDs) only go to this process's log.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError

load_dotenv()

logger = logging.getLogger("llm-provider")

DEFAULT_ANTHROPIC_MODEL = "claude-opus-5"
DEFAULT_OPENAI_MODEL = "gpt-4o"

# Non-streaming requests: ~16K output tokens keeps a call under the SDK's HTTP
# timeout. On models with adaptive thinking this budget covers thinking too.
ANTHROPIC_MAX_TOKENS = 16000

# Server-side refusal fallback: when the safety classifiers decline a request,
# the API re-runs it on the model Anthropic recommends for that refusal
# category, inside the same call. Only sent for models known to accept it; if
# you set ANTHROPIC_MODEL to another model that supports `fallbacks`, add it.
_FALLBACK_MODELS = frozenset({DEFAULT_ANTHROPIC_MODEL})
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_REQUEST_FAILED = "LLM request failed (see the agent's log for details)"
_BAD_OUTPUT = "LLM output did not match the expected schema"


class LLMError(RuntimeError):
    """An LLM call failed. The message is safe to return to A2A callers."""


class LLMProvider:
    """Generates schema-validated JSON from an LLM.

    The provider is selected with the ``LLM_PROVIDER`` env var.
    """

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "anthropic").lower()

        if self.provider == "anthropic":
            from anthropic import AsyncAnthropic

            # Reads ANTHROPIC_API_KEY (or another configured credential source).
            self.client = AsyncAnthropic()
            self.model = os.getenv("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
        elif self.provider == "openai":
            from openai import OpenAI

            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        else:
            raise ValueError(
                f"Unknown LLM_PROVIDER: {self.provider!r}. Use 'anthropic' or 'openai'."
            )

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
    ) -> dict[str, Any]:
        """Call the LLM and return its output, validated against ``output_model``.

        The result is dumped with the model's aliases (the camelCase wire
        names) and without ``None`` fields.
        """
        try:
            if self.provider == "anthropic":
                parsed = await self._generate_anthropic(
                    system_prompt, user_prompt, output_model
                )
            else:
                raw = await self._generate_openai(system_prompt, user_prompt)
                parsed = output_model.model_validate(raw)
        except LLMError:
            raise
        except ValidationError as exc:
            logger.error(
                "%s output failed %s validation: %s",
                self.provider,
                output_model.__name__,
                exc,
            )
            raise LLMError(_BAD_OUTPUT) from exc
        except Exception as exc:
            logger.error(
                "%s request failed: %s: %s", self.provider, type(exc).__name__, exc
            )
            raise LLMError(_REQUEST_FAILED) from exc

        return parsed.model_dump(mode="json", by_alias=True, exclude_none=True)

    async def _generate_anthropic(
        self,
        system_prompt: str,
        user_prompt: str,
        output_model: type[BaseModel],
    ) -> BaseModel:
        import anthropic

        extra: dict[str, Any] = {}
        if self.model in _FALLBACK_MODELS:
            extra = {"betas": [_FALLBACK_BETA], "fallbacks": "default"}

        try:
            response = await self.client.beta.messages.parse(
                model=self.model,
                max_tokens=ANTHROPIC_MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                output_format=output_model,
                **extra,
            )
        except ValidationError as exc:
            # parse() validates the text as soon as the response arrives, so a
            # reply cut off by max_tokens or a mid-output refusal fails here.
            logger.error(
                "Anthropic output failed %s validation (truncated or declined "
                "mid-output?): %s",
                output_model.__name__,
                exc,
            )
            raise LLMError(_BAD_OUTPUT) from exc
        except anthropic.AuthenticationError as exc:
            logger.error(
                "Anthropic rejected the credentials (ANTHROPIC_API_KEY): %s", exc
            )
            raise LLMError(_REQUEST_FAILED) from exc
        except anthropic.RateLimitError as exc:
            logger.error(
                "Anthropic rate limit hit (request %s): %s", exc.request_id, exc
            )
            raise LLMError(
                "LLM provider is rate limiting requests; try again later"
            ) from exc
        except anthropic.APIStatusError as exc:
            logger.error(
                "Anthropic API error HTTP %s (request %s): %s",
                exc.status_code,
                exc.request_id,
                exc,
            )
            raise LLMError(_REQUEST_FAILED) from exc
        except anthropic.APIConnectionError as exc:
            logger.error("Could not reach the Anthropic API: %s", exc)
            raise LLMError(_REQUEST_FAILED) from exc

        # Check why generation stopped before using the output.
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            logger.warning(
                "Model %s declined the request (category=%s, request %s)",
                response.model,
                getattr(details, "category", None),
                response._request_id,
            )
            raise LLMError("The LLM declined this request")
        if response.stop_reason == "max_tokens":
            logger.error(
                "Model output hit max_tokens=%d (request %s)",
                ANTHROPIC_MAX_TOKENS,
                response._request_id,
            )
            raise LLMError("LLM output was truncated")

        parsed = response.parsed_output
        if parsed is None:
            logger.error(
                "Model returned no structured output (stop_reason=%s, request %s)",
                response.stop_reason,
                response._request_id,
            )
            raise LLMError(_BAD_OUTPUT)
        return parsed

    async def _generate_openai(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        response = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
