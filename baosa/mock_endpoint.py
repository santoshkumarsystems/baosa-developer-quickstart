"""Offline, in-memory OpenAI-compatible chat completion *simulation*.

The same JSON request/response envelope used by Nebius' OpenAI-compatible API
is exercised through an httpx.MockTransport, which guarantees no network I/O.
Scripted tool decisions are educational fixtures, never Reflection AI Beam output.

Author: Santosh Kumar | MIT License."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx

SIMULATED_URL = "https://simulated-nebius.invalid/v1"
MODEL = "reflection/beam"


def _fixture_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Produce a synthetic OpenAI-compatible chat-completion response.

    Read the tools and earlier responses to select a scripted next tool call
    or explanation, preserving the expected response envelope. This is a
    deterministic educational fixture, NOT model-generated reasoning."""
    tools = {t["function"]["name"] for t in payload.get("tools", [])}
    messages = payload.get("messages", [])
    prior = [c for m in messages if m.get("role") == "assistant" for c in (m.get("tool_calls") or [])]
    names = [c["function"]["name"] for c in prior]
    results = [json.loads(m["content"]) for m in messages if m.get("role") == "tool"]
    call: tuple[str, dict[str, Any]] | None = None
    content: str | None = None
    if tools == {"check_leave"}:
        if not names:
            user = next(m["content"] for m in messages if m["role"] == "user")
            marker = 'preserve these exact values: '
            if marker not in user:
                raise ValueError("Fixed mock prompt does not contain a plan")
            parsed, _ = json.JSONDecoder().raw_decode(user.split(marker, 1)[1])
            call = ("check_leave", parsed)
        else:
            result = results[-1]
            content = ("Trusted policy: eligible for employee confirmation; manager approval remains required."
                       if result.get("eligible") else "Trusted policy blocked the request: " + result.get("reason", "unknown"))
    elif {"get_leave_balance", "get_work_schedule", "check_candidate", "propose_alternative"} <= tools:
        if "get_leave_balance" not in names:
            call = ("get_leave_balance", {})
        elif "get_work_schedule" not in names:
            call = ("get_work_schedule", {})
        elif "check_candidate" not in names:
            call = ("check_candidate", {"thursday_hours": 8, "friday_hours": 8})
        else:
            balance = next((v["available_balance_hours"] for v in results
                            if "available_balance_hours" in v), 0)
            if type(balance) is int and balance >= 8:
                call = ("propose_alternative", {"thursday_hours": min(balance - 8, 8),
                                                "friday_hours": 8})
            else:
                content = "No eligible option preserves the entire Friday."
    else:
        raise ValueError("Unexpected tool schemas")
    if call:
        name, args = call
        tool_calls = [{"id": f"sim-{len(prior)+1}", "type": "function",
                       "function": {"name": name, "arguments": json.dumps(args)}}]
    else:
        tool_calls = None
    return {"id": "chatcmpl-simulated-baosa", "object": "chat.completion",
            "created": 0, "model": MODEL,
            "choices": [{"index": 0, "finish_reason": "tool_calls" if call else "stop",
                         "message": {"role": "assistant", "content": content,
                                     "tool_calls": tool_calls, "reasoning_content": None}}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}}


class SimulatedNebiusClient:
    """Network-free model-client adapter over httpx.MockTransport.

    Exchanges JSON at an intentionally invalid hostname to verify the
    client/API protocol shape. The simulated client never connects to
    Nebius, incurs inference charges, or produces real Beam intelligence."""

    def __init__(self) -> None:
        """Initialize fixture state and expose a compatible chat-completions entry point."""
        self.calls: list[dict[str, Any]] = []
        self.transport = httpx.MockTransport(self._handle)
        self.http = httpx.Client(transport=self.transport, base_url=SIMULATED_URL,
                                 headers={"Authorization": "Bearer simulated-only"})
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def _handle(self, request: httpx.Request) -> httpx.Response:
        """Validate the simulated HTTP request and return an OpenAI-compatible response or error."""
        if request.method != "POST" or request.url.path != "/v1/chat/completions":
            return httpx.Response(404, json={"error": {"message": "Unknown simulated path"}})
        if request.headers.get("authorization") != "Bearer simulated-only":
            return httpx.Response(401, json={"error": {"message": "Invalid mock credential"}})
        try:
            payload = json.loads(request.content)
            if payload.get("model") != MODEL:
                return httpx.Response(400, json={"error": {"message": "Unexpected simulated model"}})
            return httpx.Response(200, json=_fixture_response(payload))
        except (ValueError, KeyError, TypeError) as exc:
            return httpx.Response(400, json={"error": {"message": type(exc).__name__}})

    def create(self, **kwargs: Any) -> Any:
        """Send a JSON fixture request through in-process MockTransport.

    Keep a non-sensitive request trace, decode the OpenAI-compatible
    response into SDK-shaped objects, and return synthetic tool calls.
    Do not call a remote service or infer actual model performance."""
        payload = {k: v for k, v in kwargs.items() if k != "extra_body"}
        payload.update(kwargs.get("extra_body") or {})
        # Track request shape without capturing real user credentials or secrets.
        self.calls.append({"model": payload.get("model"), "messages": len(payload.get("messages", [])),
                           "tools": [t["function"]["name"] for t in payload.get("tools", [])]})
        response = self.http.post("https://simulated-nebius.invalid/v1/chat/completions", json=payload)
        response.raise_for_status()
        raw = response.json()
        choices = []
        for choice in raw["choices"]:
            msg = choice["message"]
            calls = [SimpleNamespace(id=c["id"], type=c["type"],
                                     function=SimpleNamespace(**c["function"]))
                     for c in (msg.get("tool_calls") or [])]
            choices.append(SimpleNamespace(finish_reason=choice["finish_reason"],
                                           message=SimpleNamespace(content=msg.get("content"),
                                                                   reasoning_content=msg.get("reasoning_content"),
                                                                   tool_calls=calls)))
        return SimpleNamespace(choices=choices, usage=SimpleNamespace(**raw["usage"]))

    def close(self) -> None:
        """Release the in-memory httpx.Client and its mock transport; no network socket was opened."""
        self.http.close()
