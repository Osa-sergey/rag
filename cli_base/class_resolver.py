"""Resolve a class from a dotted path and validate base class hierarchy.

Usage::

    from cli_base.class_resolver import resolve_class

    cls = resolve_class(
        "stores.graph_store.Neo4jGraphStore",
        base_class=BaseGraphStore,
    )
    instance = cls(config)
"""
from __future__ import annotations

import importlib
from typing import Type, TypeVar

T = TypeVar("T")


def resolve_class(dotted_path: str, base_class: Type[T]) -> Type[T]:
    """Import a class by dotted path and validate it's a subclass of *base_class*.

    Supports deep inheritance — e.g. ``C(B(A))`` where ``base_class=A``.

    Args:
        dotted_path: Full dotted import path, e.g. ``"stores.graph_store.Neo4jGraphStore"``.
        base_class: Expected base class (ABC or concrete).

    Returns:
        The resolved class object.

    Raises:
        ImportError: If the module or class cannot be imported.
        TypeError: If the resolved object is not a subclass of *base_class*.
    """
    if not dotted_path or not isinstance(dotted_path, str):
        raise ImportError(f"_class_ must be a non-empty dotted path string, got: {dotted_path!r}")

    parts = dotted_path.rsplit(".", 1)
    if len(parts) != 2:
        raise ImportError(
            f"_class_ must be in 'module.ClassName' format, got: {dotted_path!r}"
        )

    module_path, class_name = parts

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise ImportError(
            f"Cannot import module '{module_path}' from _class_='{dotted_path}': {e}"
        ) from e

    cls = getattr(module, class_name, None)
    if cls is None:
        raise ImportError(
            f"Module '{module_path}' has no class '{class_name}' "
            f"(_class_='{dotted_path}')"
        )

    if not isinstance(cls, type):
        raise TypeError(
            f"'{dotted_path}' resolves to {type(cls).__name__}, not a class"
        )

    if not issubclass(cls, base_class):
        raise TypeError(
            f"Class '{dotted_path}' is not a subclass of {base_class.__name__}.\n"
            f"  Resolved: {cls.__mro__}\n"
            f"  Expected base: {base_class.__name__}"
        )

    return cls
