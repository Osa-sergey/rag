"""Tests for dagster_dsl.callbacks — callback registry and execution."""
import pytest

from dagster_dsl.callbacks import (
    CallbackConfig,
    CallbackRegistry,
    register_callback,
    execute_callbacks,
    get_retry_config,
)


@pytest.fixture(autouse=True)
def clean_callback_registry():
    """Save and restore callback registry between tests."""
    registry = CallbackRegistry()
    saved = dict(registry._callbacks)
    yield registry
    registry._callbacks = saved


# ── CallbackConfig ────────────────────────────────────────────


class TestCallbackConfig:
    def test_from_string(self):
        cb = CallbackConfig.from_yaml_item("log_result")
        assert cb.name == "log_result"
        assert cb.params == {}

    def test_from_single_key_dict(self):
        cb = CallbackConfig.from_yaml_item({"notify": {"message": "Done!"}})
        assert cb.name == "notify"
        assert cb.params == {"message": "Done!"}

    def test_from_explicit_dict(self):
        cb = CallbackConfig.from_yaml_item({
            "name": "retry",
            "params": {"max_attempts": 3, "delay": 10},
        })
        assert cb.name == "retry"
        assert cb.params == {"max_attempts": 3, "delay": 10}

    def test_from_single_key_scalar(self):
        cb = CallbackConfig.from_yaml_item({"retry": 3})
        assert cb.name == "retry"
        assert cb.params == {"value": 3}

    def test_invalid_type(self):
        with pytest.raises(TypeError):
            CallbackConfig.from_yaml_item(42)

    def test_invalid_dict(self):
        with pytest.raises(ValueError):
            CallbackConfig.from_yaml_item({"a": 1, "b": 2})


# ── CallbackRegistry ─────────────────────────────────────────


class TestCallbackRegistry:
    def test_register_and_get(self, clean_callback_registry):
        registry = clean_callback_registry

        def my_cb(**kwargs):
            pass

        registry.register("test_cb", my_cb)
        assert registry.has("test_cb")
        assert registry.get("test_cb") is my_cb

    def test_get_missing(self, clean_callback_registry):
        with pytest.raises(KeyError, match="не зарегистрирован"):
            clean_callback_registry.get("nonexistent")

    def test_decorator(self, clean_callback_registry):
        @register_callback("decorated_cb")
        def my_cb(**kwargs):
            return "ok"

        assert clean_callback_registry.has("decorated_cb")

    def test_builtin_callbacks_registered(self):
        """Built-in callbacks (log_result, notify, send_alert, retry) are registered."""
        registry = CallbackRegistry()
        assert registry.has("log_result")
        assert registry.has("notify")
        assert registry.has("send_alert")
        assert registry.has("retry")


# ── execute_callbacks ─────────────────────────────────────────


class TestExecuteCallbacks:
    def test_success_callback(self, clean_callback_registry):
        results = []

        @register_callback("test_track")
        def track(step_name, event, data, **params):
            results.append((step_name, event, data))

        cbs = [CallbackConfig(name="test_track")]
        execute_callbacks(cbs, "my.step", "success", {"count": 5})

        assert len(results) == 1
        assert results[0] == ("my.step", "success", {"count": 5})

    def test_callback_with_params(self, clean_callback_registry):
        results = []

        @register_callback("test_param")
        def with_params(step_name, event, data, **params):
            results.append(params)

        cbs = [CallbackConfig(name="test_param", params={"channel": "#test"})]
        execute_callbacks(cbs, "my.step", "failure", None)

        assert results[0]["channel"] == "#test"

    def test_missing_callback_skipped(self, clean_callback_registry):
        """Unknown callbacks are skipped with a warning, not an error."""
        cbs = [CallbackConfig(name="unknown_callback")]
        # Should not raise
        execute_callbacks(cbs, "my.step", "success", None)

    def test_retry_skipped_in_execute(self, clean_callback_registry):
        """Retry callback is skipped by execute_callbacks (handled separately)."""
        results = []

        @register_callback("test_other")
        def other(step_name, event, data, **params):
            results.append("called")

        cbs = [
            CallbackConfig(name="retry", params={"max_attempts": 3}),
            CallbackConfig(name="test_other"),
        ]
        execute_callbacks(cbs, "my.step", "failure", None)
        # Only test_other should be called, retry is skipped
        assert results == ["called"]


# ── get_retry_config ──────────────────────────────────────────


class TestGetRetryConfig:
    def test_with_retry(self):
        cbs = [
            CallbackConfig(name="log_result"),
            CallbackConfig(name="retry", params={"max_attempts": 5, "delay": 30}),
        ]
        cfg = get_retry_config(cbs)
        assert cfg == {"max_attempts": 5, "delay": 30}

    def test_without_retry(self):
        cbs = [CallbackConfig(name="log_result")]
        assert get_retry_config(cbs) is None

    def test_retry_defaults(self):
        cbs = [CallbackConfig(name="retry")]
        cfg = get_retry_config(cbs)
        assert cfg == {"max_attempts": 3, "delay": 10}
