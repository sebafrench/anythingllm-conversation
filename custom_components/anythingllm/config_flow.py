"""Configuration UI, options, reconfiguration et réauthentification."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import AnythingLLMClient, APIError, normalize_url
from .const import DEFAULT_MODE, DEFAULT_TIMEOUT, DOMAIN

PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


class AnythingLLMConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data = {}
        self._workspaces = {}
        self._editing = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return AnythingLLMOptionsFlow()

    async def async_step_user(self, user_input=None):
        return await self._credentials("user", user_input)

    async def _credentials(self, step, user_input):
        errors = {}
        if user_input is not None:
            try:
                data = {
                    "url": normalize_url(user_input["url"]),
                    "api_key": user_input["api_key"].strip(),
                }
                if not data["api_key"]:
                    raise APIError("invalid_auth")
                client = AnythingLLMClient(
                    async_get_clientsession(self.hass), **data, timeout=DEFAULT_TIMEOUT
                )
                self._workspaces = await client.workspaces()
                if not self._workspaces:
                    raise APIError("workspace_missing")
                self._data = data
                return await self.async_step_workspace()
            except APIError as err:
                errors["base"] = err.code
        default_url = self._editing.data["url"] if self._editing else "http://"
        return self.async_show_form(
            step_id=step,
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("url", default=default_url): str,
                    vol.Required("api_key"): PASSWORD,
                }
            ),
        )

    async def async_step_workspace(self, user_input=None):
        errors = {}
        if user_input is not None:
            workspace = user_input["workspace"]
            try:
                client = AnythingLLMClient(async_get_clientsession(self.hass), **self._data)
                await client.validate_workspace(workspace)
                data = {**self._data, "workspace": workspace}
                # Plusieurs entrées sont autorisées, y compris pour le même workspace.
                # Les entry_id et les slugs de threads assurent leur isolation.
                title = "AnythingLLM — " + self._workspaces.get(workspace, workspace)
                if self._editing:
                    return self.async_update_reload_and_abort(self._editing, data=data, title=title)
                return self.async_create_entry(title=title, data=data)
            except APIError as err:
                errors["base"] = err.code
        return self.async_show_form(
            step_id="workspace",
            errors=errors,
            data_schema=vol.Schema(
                {
                    vol.Required("workspace"): vol.In(self._workspaces),
                }
            ),
        )

    async def async_step_reconfigure(self, user_input=None):
        self._editing = self._get_reconfigure_entry()
        return await self._credentials("reconfigure", user_input)

    async def async_step_reauth(self, entry_data):
        self._editing = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                data = {**self._editing.data, "api_key": user_input["api_key"].strip()}
                client = AnythingLLMClient(
                    async_get_clientsession(self.hass), data["url"], data["api_key"]
                )
                await client.validate_workspace(data["workspace"])
                return self.async_update_reload_and_abort(self._editing, data=data)
            except APIError as err:
                errors["base"] = err.code
        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
            data_schema=vol.Schema({vol.Required("api_key"): PASSWORD}),
        )


class AnythingLLMOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "context_storage",
                        default=self.config_entry.options.get("context_storage", "threads"),
                    ): vol.In(
                        {
                            "threads": "Threads (recommandé)",
                            "session": "Session API — sessionId confirmé dans /api/docs",
                        }
                    ),
                    vol.Required(
                        "timeout", default=self.config_entry.options.get("timeout", DEFAULT_TIMEOUT)
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=600)),
                    vol.Required(
                        "mode", default=self.config_entry.options.get("mode", DEFAULT_MODE)
                    ): vol.In(
                        {
                            "chat": "Chat — avec historique",
                            "query": "Query — documents, sans garantie de contexte",
                        }
                    ),
                }
            ),
        )
