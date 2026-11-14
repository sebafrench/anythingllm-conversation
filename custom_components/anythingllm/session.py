"""Contexte distant isolé ; correspondances locales éphémères et bornées."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import monotonic
from uuid import uuid4

from .api import AnythingLLMClient, APIError


@dataclass
class Session:
    """Aucun historique local complet ; dernier résultat pour dédoublonnage."""

    thread: str | None = None
    touched: float = field(default_factory=monotonic)
    busy: bool = False
    request_id: str | None = None
    response: str | None = None


class Conversations:
    """Une instance par entrée, aucun état global entre entrées ou utilisateurs."""

    def __init__(
        self, client: AnythingLLMClient, workspace: str, mode: str, context_storage: str = "threads"
    ) -> None:
        self.client = client
        self.workspace = workspace
        self.mode = mode
        self.context_storage = context_storage
        self.sessions: dict[tuple, Session] = {}
        self.tasks: set[asyncio.Task] = set()
        self.closed = False

    def resolve(self, conversation_id: str | None, user: str | None, device: str | None) -> tuple:
        if self.closed:
            raise APIError("closed")
        now = monotonic()
        for key, session in list(self.sessions.items()):
            if not session.busy and now - session.touched > 3600:
                del self.sessions[key]
        key = (user, device, conversation_id)
        if conversation_id and key in self.sessions:
            return key
        if len(self.sessions) >= 128:
            raise APIError("capacity")
        # Ne jamais convertir un identifiant fourni par le client en slug distant.
        key = (user, device, uuid4().hex)
        self.sessions[key] = Session()
        return key

    async def ask(self, key: tuple, text: str, request_id: str) -> str:
        if self.closed:
            raise APIError("closed")
        session = self.sessions[key]
        if session.busy:
            raise APIError("busy")
        if session.request_id == request_id and session.response is not None:
            return session.response
        if not text.strip():
            raise APIError("empty_response")
        # @agent déclenche des capacités serveur hors du périmètre conversationnel.
        if "@agent" in text.lower():
            raise APIError("agent_disabled")
        session.busy = True
        task = asyncio.current_task()
        self.tasks.add(task)
        try:
            # Budget global création + chat, pas deux fois le délai configuré.
            async with asyncio.timeout(self.client.timeout):
                if self.context_storage == "session":
                    if session.thread is None:
                        session.thread = "ha-" + uuid4().hex
                    answer = await self.client.session_chat(
                        self.workspace, session.thread, text, self.mode
                    )
                else:
                    if session.thread is None:
                        session.thread = await self.client.new_thread(
                            self.workspace, "ha-" + uuid4().hex
                        )
                    answer = await self.client.chat(self.workspace, session.thread, text, self.mode)
            session.request_id, session.response = request_id, answer
            return answer
        except TimeoutError as err:
            self.sessions.pop(key, None)
            raise APIError("timeout") from err
        except (APIError, asyncio.CancelledError):
            # Résultat distant ambigu : ne pas réutiliser un contexte possiblement modifié.
            self.sessions.pop(key, None)
            raise
        finally:
            session.busy = False
            session.touched = monotonic()
            self.tasks.discard(task)

    async def close(self) -> None:
        self.closed = True
        tasks = list(self.tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self.sessions.clear()
