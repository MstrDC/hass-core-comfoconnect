"""Tests for the ComfoConnect config flow."""

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

from homeassistant.components.comfoconnect.config_flow import CannotConnect, InvalidAuth
from homeassistant.components.comfoconnect.const import (
    CONF_RESOURCES,
    CONF_USER_AGENT,
    DOMAIN,
)
from homeassistant.config_entries import SOURCE_IMPORT, SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_NAME, CONF_PIN, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_HOST = "192.0.2.1"
TEST_MODEL = "ComfoAir Q 350"
TEST_NAME = "Ventilation"
TEST_TOKEN = "11111111111111111111111111111111"
TEST_USER_AGENT = "Home Assistant Test"
TEST_PIN = "1234"
TEST_RESOURCES = ["current_humidity", "current_temperature"]
TEST_UUID = "00112233445566778899aabbccddeeff"


@pytest.fixture
def mock_validate_input() -> Generator[MagicMock]:
    """Mock input validation to return a fixed bridge."""
    with patch(
        "homeassistant.components.comfoconnect.config_flow._validate_input"
    ) as mock_validate:
        bridge = MagicMock()
        bridge.uuid.hex.return_value = TEST_UUID
        mock_validate.return_value = bridge
        yield mock_validate


async def test_user_step_create_entry(
    hass: HomeAssistant, mock_validate_input: MagicMock
) -> None:
    """Test a successful user step creates a config entry."""
    user_input = {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TOKEN: TEST_TOKEN,
        CONF_USER_AGENT: TEST_USER_AGENT,
        CONF_PIN: TEST_PIN,
        CONF_NAME: TEST_NAME,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data=user_input,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_MODEL
    assert result["result"].unique_id == TEST_UUID
    assert result["data"] == {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_TOKEN: TEST_TOKEN,
        CONF_USER_AGENT: TEST_USER_AGENT,
        CONF_PIN: int(TEST_PIN),
    }
    assert CONF_NAME not in result["data"]
    mock_validate_input.assert_called_once()


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (CannotConnect, "cannot_connect"),
        (InvalidAuth, "invalid_auth"),
        (Exception, "unknown"),
    ],
)
async def test_user_step_errors(
    hass: HomeAssistant,
    mock_validate_input: MagicMock,
    exception: type[Exception],
    error: str,
) -> None:
    """Test user step handles validation exceptions."""
    mock_validate_input.side_effect = exception

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: TEST_HOST, CONF_MODEL: TEST_MODEL},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": error}


async def test_user_step_already_configured(
    hass: HomeAssistant, mock_validate_input: MagicMock
) -> None:
    """Test user step aborts when the bridge is already configured."""
    MockConfigEntry(domain=DOMAIN, unique_id=TEST_UUID).add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={CONF_HOST: TEST_HOST, CONF_MODEL: TEST_MODEL},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_step_create_entry(
    hass: HomeAssistant, mock_validate_input: MagicMock
) -> None:
    """Test YAML import keeps name/resources and creates a config entry."""
    import_data = {
        CONF_HOST: TEST_HOST,
        CONF_MODEL: TEST_MODEL,
        CONF_NAME: TEST_NAME,
        CONF_RESOURCES: TEST_RESOURCES,
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_IMPORT},
        data=import_data,
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == TEST_NAME
    assert result["result"].unique_id == TEST_UUID
    assert result["data"][CONF_NAME] == TEST_NAME
    assert result["data"][CONF_RESOURCES] == TEST_RESOURCES
