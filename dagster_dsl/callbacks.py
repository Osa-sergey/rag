"""Callback system for pipeline step outcome handling.

Callbacks are invoked after step execution based on the outcome:
    - on_success: step completed without errors
    - on_failure: step raised an exception
    - on_retry:   step is being retried after failure

Built-in callbacks:
    - log_result:  Log the step result
    - retry:       Retry the step N times with delay
    - notify:      Print a notification message
    - send_alert:  Placeholder for external alerting (Slack, email, etc.)

Custom callbacks are registered via ``@register_callback("name")``.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Optional

log = logging.getLogger(__name__)


# ── Callback Config (parsed from YAML) ───────────────────────


@dataclass
class CallbackConfig:
    """A single callback invocation: name + optional parameters.

    In YAML, callbacks can be written as:
        on_success:
          - log_result              # just a name (no params)
          - notify:                 # name + params dict
              message: "Done!"
    """

    name: str
    params: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_yaml_item(cls, item: Any) -> "CallbackConfig":
        """Parse a single item from the YAML callbacks list.

        Supports two YAML formats::

            # Format 1: bare string → callback with no params
            - log_result

            # Format 2: dict with single key → callback name + params
            - notify:
                message: "Done!"

            # Format 3: dict with 'name' key → explicit
            - name: retry
              params:
                max_attempts: 3
        """
        if isinstance(item, str):
            return cls(name=item)
        elif isinstance(item, dict):
            if "name" in item:
                return cls(name=item["name"], params=item.get("params", {}))
            # Single-key dict: key=name, value=params
            if len(item) == 1:
                name = next(iter(item))
                params = item[name]
                if isinstance(params, dict):
                    return cls(name=name, params=params)
                else:
                    return cls(name=name, params={"value": params})
            raise ValueError(
                f"Invalid callback format: {item}. "
                "Expected a string, or a dict with a single key."
            )
        raise TypeError(f"Invalid callback type: {type(item)}. Expected str or dict.")


# ── Callback Function Type ───────────────────────────────────

# Callback signature: (step_name, event, result_or_error, **params) -> None
CallbackFn = Callable[..., None]


# ── Callback Registry ────────────────────────────────────────


class CallbackRegistry:
    """Singleton registry of callback functions."""

    _instance: Optional["CallbackRegistry"] = None
    _callbacks: dict[str, CallbackFn]

    def __new__(cls) -> "CallbackRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._callbacks = {}
        return cls._instance

    def register(self, name: str, fn: CallbackFn) -> None:
        self._callbacks[name] = fn
        log.debug("Registered callback: %s", name)

    def get(self, name: str) -> CallbackFn:
        if name not in self._callbacks:
            available = ", ".join(sorted(self._callbacks)) or "(none)"
            raise KeyError(
                f"Callback '{name}' не зарегистрирован. "
                f"Доступные: {available}"
            )
        return self._callbacks[name]

    def has(self, name: str) -> bool:
        return name in self._callbacks

    def list_callbacks(self) -> list[str]:
        return sorted(self._callbacks.keys())

    def clear(self) -> None:
        self._callbacks.clear()

    def __contains__(self, name: str) -> bool:
        return name in self._callbacks

    def __len__(self) -> int:
        return len(self._callbacks)


def register_callback(name: str):
    """Decorator to register a function as a named callback.

    Example::

        @register_callback("my_alert")
        def my_alert(step_name, event, data, **params):
            send_email(params.get("to"), f"Step {step_name}: {event}")
    """

    def decorator(fn: CallbackFn) -> CallbackFn:
        CallbackRegistry().register(name, fn)
        return fn

    return decorator


# ── Callback Execution ───────────────────────────────────────


def execute_callbacks(
    callbacks: list[CallbackConfig],
    step_name: str,
    event: str,
    data: Any = None,
) -> None:
    """Execute a list of callbacks for a given step event.

    Args:
        callbacks: List of CallbackConfig to invoke.
        step_name: Name of the step (e.g. "raptor_pipeline.run").
        event: Event type ("success", "failure", "retry").
        data: Result (on success) or exception (on failure).
    """
    registry = CallbackRegistry()
    for cb in callbacks:
        if cb.name == "retry":
            # Retry is handled specially by the step executor
            continue
        try:
            fn = registry.get(cb.name)
            fn(step_name=step_name, event=event, data=data, **cb.params)
        except KeyError:
            log.warning("Callback '%s' not found, skipping", cb.name)
        except Exception as e:
            log.error(
                "Callback '%s' failed for step '%s': %s",
                cb.name, step_name, e,
            )


def get_retry_config(callbacks: list[CallbackConfig]) -> Optional[dict[str, Any]]:
    """Extract retry configuration from callbacks list.

    Returns:
        Dict with 'max_attempts' and 'delay' if retry callback is present,
        None otherwise.
    """
    for cb in callbacks:
        if cb.name == "retry":
            return {
                "max_attempts": cb.params.get("max_attempts", 3),
                "delay": cb.params.get("delay", 10),
            }
    return None


# ══════════════════════════════════════════════════════════════
# Built-in Callbacks
# ══════════════════════════════════════════════════════════════


@register_callback("log_result")
def _log_result(step_name: str, event: str, data: Any = None, **params: Any) -> None:
    """Log the step result or error."""
    if event == "success":
        log.info("✅ [%s] Шаг завершён: %s", step_name, data)
    elif event == "failure":
        log.error("❌ [%s] Ошибка: %s", step_name, data)
    else:
        log.info("[%s] %s: %s", step_name, event, data)


@register_callback("notify")
def _notify(step_name: str, event: str, data: Any = None, **params: Any) -> None:
    """Print a notification message."""
    message = params.get("message", f"Step {step_name}: {event}")
    log.info("📢 %s", message)


@register_callback("send_alert")
def _send_alert(step_name: str, event: str, data: Any = None, **params: Any) -> None:
    """Placeholder for external alerting (Slack, PagerDuty, email, etc.).

    Override by registering a custom 'send_alert' callback.
    """
    channel = params.get("channel", "#general")
    log.warning(
        "🚨 ALERT [%s → %s]: %s (channel=%s) — "
        "alert dispatch not configured, override 'send_alert' callback",
        step_name, event, data, channel,
    )


@register_callback("retry")
def _retry_placeholder(step_name: str, event: str, data: Any = None, **params: Any) -> None:
    """Retry marker — actual retry logic is in execute_step_with_callbacks."""
    pass
