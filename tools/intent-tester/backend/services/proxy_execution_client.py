"""HTTP client for dispatching canonical executions to the Node proxy."""

import os
from typing import Any, Mapping, Protocol
from urllib.parse import quote

import requests


class ProxyExecutionClientError(RuntimeError):
    """Raised when the execution proxy does not explicitly accept a request."""


class _ProxyResponse(Protocol):
    status_code: int
    text: str

    @property
    def ok(self) -> bool: ...

    def json(self) -> Any: ...


class _ProxySession(Protocol):
    def post(
        self, url: str, *, json: object, timeout: float | int
    ) -> _ProxyResponse: ...

    def get(self, url: str, *, timeout: float | int) -> _ProxyResponse: ...


class ProxyExecutionClient:
    """Small replaceable boundary around the Node execution proxy API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | int | None = None,
        session: _ProxySession | None = None,
    ) -> None:
        self.base_url = (
            base_url
            or os.getenv("MIDSCENE_SERVER_URL")
            or os.getenv("MIDSCENE_API_URL")
            or "http://localhost:3001"
        ).rstrip("/")
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.getenv("MIDSCENE_API_TIMEOUT", "30"))
        )
        self.session = session or requests

    def dispatch_execution(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Dispatch one execution with its Flask-owned canonical ID."""
        return self._post("/api/execute-testcase", payload)

    def stop_execution(self, execution_id: str) -> dict[str, Any]:
        """Ask the proxy to stop exactly one canonical execution ID."""
        encoded_execution_id = quote(execution_id, safe="")
        return self._post(
            f"/api/stop-execution/{encoded_execution_id}",
            None,
        )

    def get_execution_status(self, execution_id: str) -> dict[str, Any]:
        """Read and validate one canonical execution's proxy state."""
        encoded_execution_id = quote(execution_id, safe="")
        payload = self._get(f"/api/execution-status/{encoded_execution_id}")
        if payload.get("executionId") != execution_id:
            raise ProxyExecutionClientError("proxy execution ID mismatch")
        if payload.get("status") not in {
            "running",
            "success",
            "failed",
            "stopped",
        }:
            raise ProxyExecutionClientError("proxy returned an invalid execution status")
        return payload

    def _post(
        self, path: str, payload: Mapping[str, Any] | None
    ) -> dict[str, Any]:
        try:
            response = self.session.post(
                f"{self.base_url}{path}", json=payload, timeout=self.timeout
            )
        except requests.RequestException as error:
            raise ProxyExecutionClientError(
                f"proxy network request failed: {self._compact_summary(str(error))}"
            ) from error

        return self._validate_response(response)

    def _get(self, path: str) -> dict[str, Any]:
        try:
            response = self.session.get(
                f"{self.base_url}{path}", timeout=self.timeout
            )
        except requests.RequestException as error:
            raise ProxyExecutionClientError(
                f"proxy network request failed: {self._compact_summary(str(error))}"
            ) from error

        return self._validate_response(response)

    def _validate_response(self, response: _ProxyResponse) -> dict[str, Any]:
        try:
            response_payload = response.json()
        except ValueError:
            response_payload = None

        if not response.ok:
            summary = self._response_summary(response_payload, response.text)
            raise ProxyExecutionClientError(
                f"proxy HTTP {response.status_code}: {summary}"
            )

        if not isinstance(response_payload, dict):
            raise ProxyExecutionClientError("proxy returned a non-JSON response")
        if response_payload.get("success") is not True:
            raise ProxyExecutionClientError(
                f"proxy rejected request: {self._response_summary(response_payload, '')}"
            )
        return response_payload

    @classmethod
    def _response_summary(cls, payload: object, fallback: str) -> str:
        if isinstance(payload, dict):
            for field in ("error", "message"):
                value = payload.get(field)
                if isinstance(value, str) and value.strip():
                    return cls._compact_summary(value)
        return cls._compact_summary(fallback) or "no error details"

    @staticmethod
    def _compact_summary(value: str) -> str:
        return " ".join(value.split())[:300]
