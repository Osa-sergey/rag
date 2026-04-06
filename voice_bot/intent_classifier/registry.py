"""Intent handler registry — extensible dispatch for classified intents.

The registry maps intent names to handler objects. This enables easy
extension with new domains (e.g. smart home, calendar) without
modifying the core bot code.

Usage::

    registry = IntentRegistry()
    registry.register(FireflyExpenseHandler(...))
    registry.register(FireflyTransferHandler(...))
    registry.register(SmartHomeHandler(...))  # future

    # In bot handler:
    result = await registry.dispatch("expense", text)
"""
from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class IntentHandler(Protocol):
    """Protocol for intent handlers.

    Any object that has ``intent_name`` and ``handle()`` matches.
    """

    @property
    def intent_name(self) -> str:
        """The intent name this handler processes (e.g. 'expense')."""
        ...

    async def handle(self, text: str, **kwargs) -> Any:
        """Process the classified text and return a result."""
        ...


class IntentRegistry:
    """Registry mapping intent names → handlers.

    Supports registering multiple handlers per intent (first wins).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, IntentHandler] = {}

    def register(self, handler: IntentHandler) -> None:
        """Register a handler for its declared intent_name."""
        name = handler.intent_name
        if name in self._handlers:
            logger.warning(
                "Overwriting handler for intent '%s': %s → %s",
                name,
                type(self._handlers[name]).__name__,
                type(handler).__name__,
            )
        self._handlers[name] = handler
        logger.info(
            "Registered handler '%s' for intent '%s'",
            type(handler).__name__, name,
        )

    def get_handler(self, intent_name: str) -> IntentHandler | None:
        """Get the handler for an intent name, or None."""
        return self._handlers.get(intent_name)

    async def dispatch(self, intent_name: str, text: str, **kwargs) -> Any:
        """Dispatch text to the appropriate handler.

        Returns the handler's result, or None if no handler is registered.
        """
        handler = self._handlers.get(intent_name)
        if handler is None:
            logger.warning("No handler registered for intent '%s'", intent_name)
            return None

        logger.info("Dispatching intent '%s' to %s", intent_name, type(handler).__name__)
        return await handler.handle(text, **kwargs)

    @property
    def registered_intents(self) -> list[str]:
        """List all registered intent names."""
        return list(self._handlers.keys())

    def __contains__(self, intent_name: str) -> bool:
        return intent_name in self._handlers

    def __len__(self) -> int:
        return len(self._handlers)
