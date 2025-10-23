"""Mock Home Assistant modules for CI testing."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict
from unittest.mock import MagicMock


class FlowResultType(Enum):
    """Mock FlowResultType enum."""

    FORM = "form"
    CREATE_ENTRY = "create_entry"
    ABORT = "abort"


class FlowResult:
    """Mock FlowResult class."""

    def __init__(self, flow_id: str, type: FlowResultType, data: dict = None):
        self.flow_id = flow_id
        self.type = type
        self.data = data or {}

    def __getitem__(self, key):
        """Make FlowResult subscriptable like a dictionary."""
        if key == "type":
            return self.type
        elif key == "data":
            if self.type == FlowResultType.CREATE_ENTRY:
                data_without_title = self.data.copy()
                data_without_title.pop("title", None)
                return data_without_title
            return self.data
        elif key == "flow_id":
            return self.flow_id
        elif key == "step_id":
            return self.data.get("step_id")
        elif key == "errors":
            return self.data.get("errors")
        elif key == "title":
            return self.data.get("title")
        else:
            return self.data.get(key)

    def get(self, key, default=None):
        """Support dict.get() method."""
        try:
            return self[key]
        except (KeyError, TypeError):
            return default

    def __contains__(self, key):
        """Support 'key in result' checks."""
        if key in ("type", "data", "flow_id"):
            return True
        return key in self.data


class HomeAssistant:
    """Mock HomeAssistant class."""

    def __init__(self, config_dir: str = ""):
        self.config_dir = config_dir
        self.data: Dict[str, Any] = {}
        self.config_entries = MagicMock()
        self.entity_registry = MagicMock()
        self.device_registry = MagicMock()

    async def async_start(self):
        """Mock async_start."""
        pass

    async def async_stop(self):
        """Mock async_stop."""
        pass


class ConfigEntry:
    """Mock ConfigEntry class."""

    def __init__(self, **kwargs):
        self.entry_id = kwargs.get("entry_id", "test_entry_id")
        self.data = kwargs.get("data", {})
        self.options = kwargs.get("options", {})
        self.title = kwargs.get("title", "Test Entry")
        self.domain = kwargs.get("domain", "fireboard")
        self.source = kwargs.get("source", "user")
        self.version = kwargs.get("version", 1)
        self.minor_version = kwargs.get("minor_version", 1)
        self.unique_id = kwargs.get("unique_id")

    def add_to_hass(self, hass):
        """Mock add_to_hass method."""
        pass


class ConfigFlow:
    """Mock ConfigFlow class."""

    def __init__(self, *args, **kwargs):
        pass

    def __init_subclass__(cls, domain=None, **kwargs):
        """Mock __init_subclass__ to handle domain parameter."""
        cls.domain = domain
        super().__init_subclass__(**kwargs)

    def async_show_form(self, step_id, data_schema=None, errors=None):
        """Mock async_show_form method."""
        data = {"step_id": step_id}
        if errors:
            data["errors"] = errors
        return FlowResult("test_flow", FlowResultType.FORM, data)

    def async_create_entry(self, title, data):
        """Mock async_create_entry method."""
        data_with_title = data.copy()
        data_with_title["title"] = title
        return FlowResult("test_flow", FlowResultType.CREATE_ENTRY, data_with_title)

    def async_abort(self, reason):
        """Mock async_abort method."""
        return FlowResult("test_flow", FlowResultType.ABORT, {"reason": reason})


class DeviceInfo:
    """Mock DeviceInfo class."""

    def __init__(self, **kwargs):
        self.identifiers = kwargs.get("identifiers", set())
        self.manufacturer = kwargs.get("manufacturer", "")
        self.model = kwargs.get("model", "")
        self.name = kwargs.get("name", "")
        self.sw_version = kwargs.get("sw_version", "")


class DataUpdateCoordinator:
    """Mock DataUpdateCoordinator class."""

    def __init__(self, hass: HomeAssistant, logger=None, **kwargs):
        self.hass = hass
        self.logger = logger
        self.data = {}
        self.last_update_success = True

    async def async_config_entry_first_refresh(self):
        """Mock async_config_entry_first_refresh."""
        pass

    async def async_request_refresh(self):
        """Mock async_request_refresh."""
        pass

    def __class_getitem__(self, item):
        """Support generic type parameters."""
        return self


class UpdateFailed(Exception):
    """Mock UpdateFailed exception."""

    pass


class ConfigEntryNotReady(Exception):
    """Mock ConfigEntryNotReady exception."""

    pass


class HomeAssistantError(Exception):
    """Mock HomeAssistantError exception."""

    pass


class BinarySensorEntity:
    """Mock BinarySensorEntity class."""

    pass


class SensorEntity:
    """Mock SensorEntity class."""

    pass


class CoordinatorEntity:
    """Mock CoordinatorEntity class."""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._attr_unique_id = None
        self._attr_name = None

    @property
    def unique_id(self):
        return self._attr_unique_id

    @property
    def name(self):
        return self._attr_name


class Entity:
    """Mock Entity class."""

    pass


# Mock constants
class Platform(Enum):
    """Mock Platform enum."""

    BINARY_SENSOR = "binary_sensor"
    SENSOR = "sensor"


class UnitOfTemperature:
    """Mock UnitOfTemperature enum."""

    FAHRENHEIT = "°F"
    CELSIUS = "°C"


class BinarySensorDeviceClass:
    """Mock BinarySensorDeviceClass enum."""

    CONNECTIVITY = "connectivity"
    BATTERY = "battery"


class SensorDeviceClass:
    """Mock SensorDeviceClass enum."""

    TEMPERATURE = "temperature"
    BATTERY = "battery"


class SensorStateClass:
    """Mock SensorStateClass enum."""

    MEASUREMENT = "measurement"


class EntityCategory:
    """Mock EntityCategory enum."""

    DIAGNOSTIC = "diagnostic"


# Mock configuration constants
CONF_EMAIL = "email"
CONF_PASSWORD = "password"


class MockModule:
    """Mock module class."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockVoluptuous:
    """Mock voluptuous module."""

    def __getattr__(self, name):
        """Mock any voluptuous attribute."""
        return lambda *args, **kwargs: None


# Mock the homeassistant module structure
homeassistant = MockModule(
    core=MockModule(HomeAssistant=HomeAssistant),
    config_entries=MockModule(ConfigEntry=ConfigEntry, ConfigFlow=ConfigFlow),
    data_entry_flow=MockModule(FlowResultType=FlowResultType, FlowResult=FlowResult),
    exceptions=MockModule(
        HomeAssistantError=HomeAssistantError,
        ConfigEntryNotReady=ConfigEntryNotReady,
    ),
    const=MockModule(
        Platform=Platform,
        UnitOfTemperature=UnitOfTemperature,
        CONF_EMAIL=CONF_EMAIL,
        CONF_PASSWORD=CONF_PASSWORD,
    ),
    helpers=MockModule(
        entity=MockModule(
            DeviceInfo=DeviceInfo,
            Entity=Entity,
        ),
        update_coordinator=MockModule(
            DataUpdateCoordinator=DataUpdateCoordinator,
            UpdateFailed=UpdateFailed,
            CoordinatorEntity=CoordinatorEntity,
        ),
    ),
    components=MockModule(
        binary_sensor=MockModule(
            BinarySensorEntity=BinarySensorEntity,
            BinarySensorDeviceClass=BinarySensorDeviceClass,
        ),
        sensor=MockModule(
            SensorEntity=SensorEntity,
            SensorDeviceClass=SensorDeviceClass,
            SensorStateClass=SensorStateClass,
        ),
    ),
)

# Mock external dependencies
voluptuous = MockVoluptuous()

