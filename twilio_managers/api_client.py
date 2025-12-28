"""
Facilitates requests to the sms API by handling stuff like auth, URL composition, etc.
"""

import abc
import os
from typing import Any

import requests

from twilio_managers import platform_info


class CredentialsNotFoundException(Exception):
    """
    Username or password for the api is missing.
    """


class RestApiClient:
    """
    Client for invoking endpoints in this app with basic auth.
    """

    def __init__(self) -> None:
        platform_info.install_environment_variables()
        self.api_base = (
            f"{platform_info.get_protocol()}://{platform_info.get_api_domain()}"
        )

    def invoke(
        self,
        resource: str,
        request_type: str = "get",
        payload: dict[str, Any] | None = None,
        timeout: int = 10,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Makes a request to the resource (example: sms/webhook) with the specified request_type and payload dict.
        """
        if payload is None:
            payload = {}

        url = os.path.join(self.api_base, resource)
        if url[-1] != "/":
            url += "/"

        client_method = getattr(requests, request_type)
        response = client_method(
            url, auth=self.get_auth(), json=payload, timeout=timeout, **kwargs
        )
        response.raise_for_status()
        response_dict = response.json()

        return dict(response_dict)

    @abc.abstractmethod
    def get_auth(self) -> tuple[str, str]:
        """
        Returns a tuple consisting of the username and password.
        """


class TwilioManagerApiClient(RestApiClient):
    def get_auth(self) -> tuple[str, str]:
        """
        Returns a tuple consisting of the username and password.
        """
        try:
            username = os.environ["SMS_SENDER_API_USERNAME"]
            password = os.environ["SMS_SENDER_API_PASSWORD"]
        except KeyError as e:
            raise CredentialsNotFoundException(e)

        return username, password
