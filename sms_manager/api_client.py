"""
Facilitates requests to the sms API by handling stuff like auth, URL composition, etc.
"""

import os
import requests

import platform_info


class CredentialsNotFoundException(Exception):
    """
    Username or password for the api is missing.
    """


class RestApiClient(object):
    """
    Client for invoking endpoints in this app with basic auth.
    """

    def __init__(self):
        platform_info.install_environment_variables()
        self.api_base = "{}://{}".format(
            platform_info.get_protocol(), platform_info.get_api_domain()
        )

    def invoke(self, resource, request_type="get", payload=None, timeout=10, **kwargs):
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

    def get_auth(self):
        """
        Returns a tuple consisting of the username and password.
        """
        try:
            username = os.environ["REST_API_USERNAME"]
            password = os.environ["REST_API_PASSWORD"]
        except KeyError as e:
            raise CredentialsNotFoundException(e)

        return username, password
