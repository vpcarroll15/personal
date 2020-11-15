"""
This is a wrapper that helps the sms manager to determine where it should get/post data.
"""
import os

import dotenv

# TODO: Generalize this if we have to run it in multiple environments (unlikely).
ENV_FILE_PATH = "/home/ubuntu/environment.env"


def get_protocol():
    return os.environ.get("API_PROTOCOL", "http")


def get_api_domain():
    return os.environ.get("API_DOMAIN", "localhost:8000")


def install_environment_variables(path=ENV_FILE_PATH):
    """
    Add variables from this .env file to Python's os.environ.
    Doesn't complain if the file doesn't exist.
    """
    success_flag = dotenv.load_dotenv(path, override=True)
    return success_flag
