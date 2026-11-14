"""Client non streaming. Aucun retry, aucune journalisation des charges utiles."""

from __future__ import annotations

from urllib.parse import quote, unquote, urlsplit, urlunsplit

import aiohttp

from .const import ERRORS


class APIError(Exception):
    """Erreur publique sans URL, clé, conversation ou corps de réponse."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(ERRORS[code])


def normalize_url(value: str) -> str:
    """Accepter une racine, un préfixe reverse proxy, /api ou /api/v1."""
    try:
        value = value.strip()
        parts = urlsplit(value)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or any(c.isspace() for c in value)
            or "\\" in value
        ):
            raise ValueError
        _ = parts.port
        path = parts.path.rstrip("/")
        if any(unquote(s) in (".", "..") for s in path.split("/")):
            raise ValueError
        if path.endswith("/api/v1"):
            path = path[:-7]
        elif path.endswith("/api"):
            path = path[:-4]
        elif path.endswith("/api/docs"):
            raise ValueError
        return urlunsplit((parts.scheme, parts.netloc.lower(), path, "", ""))
    except (ValueError, AttributeError) as err:
        raise APIError("invalid_url") from err


class AnythingLLMClient:
    """Utilise la session partagée de Home Assistant, sans la fermer."""

    def __init__(
        self, session: aiohttp.ClientSession, url: str, api_key: str, timeout: int = 120
    ) -> None:
        self.session = session
        self.url = normalize_url(url)
        if not api_key.strip() or "\r" in api_key or "\n" in api_key:
            raise APIError("invalid_auth")
        self._key = api_key.strip()
        self.timeout = timeout

    async def request(self, method: str, *segments: str, payload=None) -> dict:
        url = self.url + "/api/v1/" + "/".join(quote(s, safe="") for s in segments)
        try:
            async with self.session.request(
                method,
                url,
                json=payload,
                headers={"Authorization": f"Bearer {self._key}"},
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                allow_redirects=False,
            ) as response:
                status = response.status
                if status in (401, 403):
                    raise APIError("invalid_auth")
                if status == 404:
                    raise APIError("not_found")
                if status == 429:
                    raise APIError("rate_limited")
                if status >= 500:
                    raise APIError("server_error")
                if not 200 <= status < 300:
                    raise APIError("request_failed")
                try:
                    result = await response.json()
                except (ValueError, aiohttp.ContentTypeError, UnicodeError) as err:
                    raise APIError("invalid_response") from err
                if not isinstance(result, dict):
                    raise APIError("invalid_response")
                return result
        except TimeoutError as err:
            raise APIError("timeout") from err
        except aiohttp.ClientError as err:
            raise APIError("cannot_connect") from err

    async def workspaces(self) -> dict[str, str]:
        auth = await self.request("GET", "auth")
        if auth.get("authenticated") is not True:
            raise APIError("invalid_auth")
        data = await self.request("GET", "workspaces")
        rows = data.get("workspaces")
        if not isinstance(rows, list):
            raise APIError("invalid_response")
        result = {}
        for row in rows:
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("slug"), str)
                or not row["slug"]
                or not isinstance(row.get("name"), str)
            ):
                raise APIError("invalid_response")
            result[row["slug"]] = row["name"]
        return result

    async def validate_workspace(self, workspace: str) -> None:
        if workspace not in await self.workspaces():
            raise APIError("workspace_missing")

    async def new_thread(self, workspace: str, slug: str) -> str:
        try:
            data = await self.request(
                "POST",
                "workspace",
                workspace,
                "thread",
                "new",
                payload={"name": "Home Assistant", "slug": slug},
            )
        except APIError as err:
            if err.code == "not_found":
                raise APIError("threads_required") from err
            raise
        thread = data.get("thread")
        if not isinstance(thread, dict) or thread.get("slug") != slug:
            raise APIError("invalid_response")
        return slug

    async def chat(self, workspace: str, thread: str, message: str, mode: str) -> str:
        data = await self.request(
            "POST",
            "workspace",
            workspace,
            "thread",
            thread,
            "chat",
            payload={"message": message, "mode": mode},
        )
        return self.parse_answer(data)

    async def session_chat(self, workspace: str, session_id: str, message: str, mode: str) -> str:
        """Repli explicite, uniquement sur API garantissant sessionId."""
        data = await self.request(
            "POST",
            "workspace",
            workspace,
            "chat",
            payload={"message": message, "mode": mode, "sessionId": session_id},
        )
        return self.parse_answer(data)

    @staticmethod
    def parse_answer(data: dict) -> str:
        if data.get("error") or data.get("type") == "abort":
            raise APIError("request_failed")
        if data.get("type") != "textResponse" or not isinstance(data.get("textResponse"), str):
            raise APIError("invalid_response")
        text = data["textResponse"].strip()
        if not text:
            raise APIError("empty_response")
        return text
