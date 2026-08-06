"""Tests for the ComfoConnect integration setup."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.comfoconnect.const import (
    CONF_RESOURCES,
    CONF_USER_AGENT,
    DEFAULT_NAME,
    DEFAULT_PIN,
    DEFAULT_TOKEN,
    DEFAULT_USER_AGENT,
    DOMAIN,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    CONF_HOST,
    CONF_MODEL,
    CONF_PIN,
    CONF_PLATFORM,
    CONF_TOKEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry

TEST_HOST = "192.0.2.1"
TEST_UUID = "00112233445566778899aabbccddeeff"


@pytest.fixture
def mock_bridge_discover() -> Generator[MagicMock]:
    """Mock bridge discovery to return one bridge."""
    with patch(
        "homeassistant.components.comfoconnect.Bridge.discover"
    ) as mock_discover:
        bridge = MagicMock()
        bridge.uuid.hex.return_value = TEST_UUID
        mock_discover.return_value = [bridge]
        yield mock_discover


@pytest.fixture
def mock_connect() -> Generator[MagicMock]:
    """Mock ComfoConnect connect."""
    with patch("homeassistant.components.comfoconnect.ComfoConnect.connect") as mock:
        yield mock


@pytest.fixture
def mock_disconnect() -> Generator[MagicMock]:
    """Mock ComfoConnect disconnect."""
    with patch("homeassistant.components.comfoconnect.ComfoConnect.disconnect") as mock:
        yield mock


@pytest.fixture
def mock_register_sensor() -> Generator[MagicMock]:
    """Mock sensor registration called by sensor/fan platforms."""
    with patch(
        "homeassistant.components.comfoconnect.ComfoConnect.register_sensor"
    ) as mock:
        yield mock


async def test_setup_and_unload_entry(
    hass: HomeAssistant,
    mock_bridge_discover: MagicMock,
    mock_connect: MagicMock,
    mock_disconnect: MagicMock,
    mock_register_sensor: MagicMock,
) -> None:
    """Test config entry setup and unload."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    mock_bridge_discover.assert_called_once_with(TEST_HOST)
    mock_connect.assert_called_once()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_disconnect.assert_called_once()


async def test_setup_entry_not_ready_when_discovery_fails(hass: HomeAssistant) -> None:
    """Test setup retries when bridge discovery fails."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.comfoconnect.Bridge.discover", return_value=[]
    ):
        await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_not_ready_when_connect_fails(
    hass: HomeAssistant,
    mock_bridge_discover: MagicMock,
    mock_register_sensor: MagicMock,
) -> None:
    """Test setup retries when connect fails."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.comfoconnect.ComfoConnect.connect",
        side_effect=RuntimeError,
    ):
        await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_yaml_setup_preserves_legacy_sensor_resources(
    hass: HomeAssistant,
) -> None:
    """Test YAML setup forwards legacy sensor resources to import flow data."""
    resources = ["current_humidity", "power_usage"]
    config = {
        DOMAIN: {CONF_HOST: TEST_HOST},
        SENSOR_DOMAIN: {
            CONF_PLATFORM: DOMAIN,
            CONF_RESOURCES: resources,
        },
    }

    with patch(
        "homeassistant.components.comfoconnect.async_setup_import"
    ) as mock_setup_import:
        assert await async_setup_component(hass, DOMAIN, config)
        await hass.async_block_till_done()

    mock_setup_import.assert_called_once_with(
        hass,
        {
            CONF_HOST: TEST_HOST,
            CONF_MODEL: DEFAULT_NAME,
            CONF_TOKEN: DEFAULT_TOKEN,
            CONF_PIN: DEFAULT_PIN,
            CONF_USER_AGENT: DEFAULT_USER_AGENT,
            CONF_RESOURCES: resources,
        },
    )
