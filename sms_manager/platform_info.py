"""
This is a wrapper that helps the sms manager to determine where it should get/post data.
"""
import os

def get_protocol():
    return os.environ.get("API_PROTOCOL", "http")


def get_api_domain():
    return os.environ.get("API_DOMAIN", "localhost:8000")
