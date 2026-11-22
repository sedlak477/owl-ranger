import pytest

from adapters import get_adapter
from adapters import wait_adapter
from adapters.wait_adapter import WaitAdapter


def test_registered_as_wait():
    adapter = get_adapter("wait", "w", duration="0.5")
    assert isinstance(adapter, WaitAdapter)
    assert adapter.duration == 0.5


def test_measure_sleeps_for_duration(monkeypatch):
    calls = []
    monkeypatch.setattr(wait_adapter, "sleep", calls.append)
    with WaitAdapter("w", duration="1.5") as adapter:
        assert adapter.measure() == {"status": "success"}
        assert adapter.measure() == {"status": "success"}
    assert calls == [1.5, 1.5]


def test_duration_recorded_in_config():
    assert WaitAdapter("w", duration="2").config["duration"] == 2.0


def test_duration_required():
    with pytest.raises(TypeError):
        get_adapter("wait", "w")


@pytest.mark.parametrize("duration", ["-1", "abc"])
def test_invalid_duration_rejected(duration):
    with pytest.raises(ValueError):
        WaitAdapter("w", duration=duration)
