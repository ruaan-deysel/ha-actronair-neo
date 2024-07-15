"""The Actron Air Neo integration."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_UPDATE_INTERVAL
from .api import ActronApi, AuthenticationError, ApiError
from .coordinator import ActronDataCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Actron Air Neo component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Actron Air Neo from a config entry."""
    for attempt in range(3):  # Try setup up to 3 times
        try:
            api = ActronApi(
                username=entry.data[CONF_USERNAME],
                password=entry.data[CONF_PASSWORD]
            )

            await api.authenticate()

            update_interval = entry.options.get("update_interval", DEFAULT_UPDATE_INTERVAL)
            coordinator = ActronDataCoordinator(
                hass,
                api,
                entry.data[CONF_DEVICE_ID],
                update_interval
            )

            await coordinator.async_config_entry_first_refresh()

            hass.data[DOMAIN][entry.entry_id] = coordinator

            await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

            entry.async_on_unload(entry.add_update_listener(update_listener))
            return True
        except AuthenticationError as auth_err:
            _LOGGER.error("Authentication error: %s", auth_err)
            if attempt == 2:  # Last attempt
                raise ConfigEntryNotReady("Authentication failed") from auth_err
        except ApiError as api_err:
            _LOGGER.error("API error: %s", api_err)
            if attempt == 2:  # Last attempt
                raise ConfigEntryNotReady("Failed to communicate with Actron API") from api_err
        except Exception as exc:
            _LOGGER.error("Unexpected error setting up Actron Air Neo integration: %s", exc)
            if attempt == 2:  # Last attempt
                raise ConfigEntryNotReady("Unexpected error occurred") from exc
        
        _LOGGER.info(f"Retrying setup (attempt {attempt + 2}/3)...")
        await asyncio.sleep(5)  # Wait 5 seconds before retrying

    return False

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.api.close()
    return unload_ok

async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
        new = {**config_entry.data}
        # TODO: modify the data if needed for version migration

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

    _LOGGER.info("Migration to version %s successful", config_entry.version)

    return True