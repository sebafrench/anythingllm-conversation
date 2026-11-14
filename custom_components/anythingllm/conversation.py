"""Agent Assist textuel ; aucun outil ni appel de service domotique."""

from homeassistant.components import conversation
from homeassistant.helpers import intent

from .api import APIError


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    async_add_entities([AnythingLLMConversation(entry)])


class AnythingLLMConversation(conversation.ConversationEntity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, entry) -> None:
        self.entry = entry
        self.manager = entry.runtime_data
        self._attr_unique_id = entry.entry_id
        self._attr_name = entry.title

    @property
    def supported_languages(self) -> list[str]:
        return ["fr"]

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await self.manager.close()
        await super().async_will_remove_from_hass()

    async def async_process(self, user_input):
        response = intent.IntentResponse(language=user_input.language)
        conversation_id = None
        try:
            key = self.manager.resolve(
                user_input.conversation_id, user_input.context.user_id, user_input.device_id
            )
            conversation_id = key[2]
            answer = await self.manager.ask(key, user_input.text, user_input.context.id)
            response.async_set_speech(answer)
        except APIError as err:
            if err.code == "invalid_auth":
                self.entry.async_start_reauth(self.hass)
            response.async_set_error(intent.IntentResponseErrorCode.UNKNOWN, str(err))
        return conversation.ConversationResult(response=response, conversation_id=conversation_id)
