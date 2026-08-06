"""Tests for the comfoconnect sensor platform."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.comfoconnect.const import CONF_RESOURCES, DOMAIN
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry

VALID_RESOURCES = [
    "current_humidity",
    "current_temperature",
    "supply_fan_duty",
    "power_usage",
    "preheater_power_total",
]


@pytest.fixture
def mock_bridge_discover() -> Generator[MagicMock]:
    """Mock the bridge discover method."""
    with patch("pycomfoconnect.bridge.Bridge.discover") as mock_bridge_discover:
        bridge = MagicMock()
        bridge.uuid.hex.return_value = "00"
        bridge.host = "192.0.2.1"
        mock_bridge_discover.return_value = [bridge]
        yield mock_bridge_discover


@pytest.fixture
def mock_comfoconnect_command() -> Generator[MagicMock]:
    """Mock the ComfoConnect register_sensor method."""
    with patch(
        "pycomfoconnect.comfoconnect.ComfoConnect.register_sensor"
    ) as mock_comfoconnect_command:
        yield mock_comfoconnect_command


@pytest.fixture
def mock_comfoconnect_connect() -> Generator[MagicMock]:
    """Mock the ComfoConnect connect method."""
    with patch("pycomfoconnect.comfoconnect.ComfoConnect.connect") as mock_connect:
        yield mock_connect


@pytest.fixture(autouse=True)
def mock_comfoconnect_disconnect() -> Generator[MagicMock]:
    """Mock the ComfoConnect disconnect method, autouse=True to mock in teardown."""
    with patch(
        "pycomfoconnect.comfoconnect.ComfoConnect.disconnect"
    ) as mock_disconnect:
        yield mock_disconnect


@pytest.fixture
async def setup_sensor(
    hass: HomeAssistant,
    mock_bridge_discover: MagicMock,
    mock_comfoconnect_command: MagicMock,
    mock_comfoconnect_connect: MagicMock,
) -> None:
    """Set up ComfoConnect integration from a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="ComfoAir Q",
        data={
            CONF_HOST: "192.0.2.1",
            CONF_RESOURCES: VALID_RESOURCES,
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_preserves_user_entity_name_and_clears_stale_original_name(
    hass: HomeAssistant,
    mock_bridge_discover: MagicMock,
    mock_comfoconnect_command: MagicMock,
    mock_comfoconnect_connect: MagicMock,
) -> None:
    """Test setup preserves user customizations but clears stale integration metadata."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "192.0.2.1"})
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    entity_entry = entity_registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "unique-id",
        config_entry=entry,
        suggested_object_id="test_sensor",
        original_name="Stale name",
    )
    entity_registry.async_update_entity(entity_entry.entity_id, name="User custom name")

    with patch.object(
        hass.config_entries, "async_forward_entry_setups", return_value=True
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)

    updated_entry = entity_registry.async_get(entity_entry.entity_id)
    assert updated_entry is not None
    assert updated_entry.name == "User custom name"
    assert updated_entry.original_name is None


@pytest.mark.usefixtures("setup_sensor")
async def test_sensors(hass: HomeAssistant) -> None:
    """Test the sensors."""
    assert hass.states.get("sensor.comfoair_q_outside_temperature") is None

    state = hass.states.get("sensor.comfoair_q_inside_humidity")
    assert state is not None
    assert state.name == "ComfoAir Q Inside humidity"
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.attributes.get("device_class") == "humidity"
    assert state.attributes.get("icon") is None

    state = hass.states.get("sensor.comfoair_q_inside_temperature")
    assert state is not None
    assert state.name == "ComfoAir Q Inside temperature"
    assert state.attributes.get("unit_of_measurement") == "°C"
    assert state.attributes.get("device_class") == "temperature"
    assert state.attributes.get("icon") is None

    state = hass.states.get("sensor.comfoair_q_supply_fan_duty")
    assert state is not None
    assert state.name == "ComfoAir Q Supply fan duty"
    assert state.attributes.get("unit_of_measurement") == "%"
    assert state.attributes.get("device_class") is None
    assert state.attributes.get("icon") == "mdi:fan-plus"

    state = hass.states.get("sensor.comfoair_q_power_usage")
    assert state is not None
    assert state.name == "ComfoAir Q Power usage"
    assert state.attributes.get("unit_of_measurement") == "W"
    assert state.attributes.get("device_class") == "power"
    assert state.attributes.get("icon") is None

    state = hass.states.get("sensor.comfoair_q_preheater_energy_total")
    assert state is not None
    assert state.name == "ComfoAir Q Preheater energy total"
    assert state.attributes.get("unit_of_measurement") == "kWh"
    assert state.attributes.get("device_class") == "energy"
    assert state.attributes.get("icon") is None
