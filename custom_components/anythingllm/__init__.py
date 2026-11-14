"""AnythingLLM Conversation : chargement et déchargement sans polling."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AnythingLLMClient, APIError
from .const import DEFAULT_MODE, DEFAULT_TIMEOUT
from .session import Conversations

PLATFORMS = [Platform.CONVERSATION]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    try:
        client = AnythingLLMClient(
            async_get_clientsession(hass),
            entry.data["url"],
            entry.data["api_key"],
            entry.options.get("timeout", DEFAULT_TIMEOUT),
        )
        await client.validate_workspace(entry.data["workspace"])
    except APIError as err:
        if err.code == "invalid_auth":
            raise ConfigEntryAuthFailed(str(err)) from None
        if err.code in ("cannot_connect", "timeout", "rate_limited", "server_error"):
            raise ConfigEntryNotReady(str(err)) from None
        raise ConfigEntryError(str(err)) from None
    entry.runtime_data = Conversations(
        client,
        entry.data["workspace"],
        entry.options.get("mode", DEFAULT_MODE),
        entry.options.get("context_storage", "threads"),
    )
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await entry.runtime_data.close()
        raise
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.close()
        return True
    return False
