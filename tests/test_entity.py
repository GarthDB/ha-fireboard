"""Tests for the FireBoard base entity."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.fireboard.const import DOMAIN
from custom_components.fireboard.entity import FireBoardEntity


def _make_coordinator(data, last_update_success=True):
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = last_update_success
    return coordinator


def test_entity_reads_title_and_model_from_coordinator_data(mock_coordinator_data):
    """Test __init__ pulls the device title/model out of coordinator data."""
    coordinator = _make_coordinator(mock_coordinator_data)

    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    assert entity._device_title == "Test FireBoard"
    assert entity._device_model == "FireBoard 2 Pro"


def test_entity_falls_back_to_defaults_when_device_missing():
    """Test __init__ falls back to defaults when the device isn't in data yet."""
    coordinator = _make_coordinator({})

    entity = FireBoardEntity(coordinator, "unknown-device-uuid")

    assert entity._device_title == "FireBoard"
    assert entity._device_model == "Unknown"


def test_device_info_property(mock_coordinator_data):
    """Test device_info exposes identifiers, naming, and software version."""
    coordinator = _make_coordinator(mock_coordinator_data)
    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    device_info = entity.device_info

    assert device_info.identifiers == {(DOMAIN, "test-device-uuid-123")}
    assert device_info.name == "Test FireBoard"
    assert device_info.manufacturer == "FireBoard"
    assert device_info.model == "FireBoard 2 Pro"
    assert device_info.sw_version == "1.0.0"


def test_available_when_online_and_update_successful(mock_coordinator_data):
    """Test available is True when the coordinator is healthy and device online."""
    coordinator = _make_coordinator(mock_coordinator_data)
    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    assert entity.available is True


def test_unavailable_when_device_offline(mock_coordinator_data):
    """Test available is False when the device itself is marked offline."""
    mock_coordinator_data["test-device-uuid-123"]["online"] = False
    coordinator = _make_coordinator(mock_coordinator_data)
    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    assert entity.available is False


def test_unavailable_when_last_update_failed(mock_coordinator_data):
    """Test available is False whenever the last coordinator refresh failed.

    This holds regardless of the device's own online flag.
    """
    coordinator = _make_coordinator(mock_coordinator_data, last_update_success=False)
    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    assert entity.available is False


def test_device_data_and_temperatures_properties(mock_coordinator_data):
    """Test _device_data and _temperatures read through to coordinator data."""
    coordinator = _make_coordinator(mock_coordinator_data)
    entity = FireBoardEntity(coordinator, "test-device-uuid-123")

    assert entity._device_data == mock_coordinator_data["test-device-uuid-123"]
    assert (
        entity._temperatures
        == mock_coordinator_data["test-device-uuid-123"]["temperatures"]
    )


def test_temperatures_property_empty_for_unknown_device():
    """Test _temperatures returns {} rather than raising for an unknown device."""
    coordinator = _make_coordinator({})
    entity = FireBoardEntity(coordinator, "unknown-device-uuid")

    assert entity._temperatures == {}
