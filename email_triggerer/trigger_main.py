"""
Trigger the service that generates prayer emails.
"""

import logging
import os
import time

import dotenv
import requests

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


def run_cycle():
    url = f"{get_protocol()}://{get_api_domain()}/prayer/trigger/"
    username = os.environ["EMAIL_TRIGGERER_API_USERNAME"]
    password = os.environ["EMAIL_TRIGGERER_API_PASSWORD"]

    response = requests.post(url, auth=(username, password), json={}, timeout=10)
    response.raise_for_status()


if __name__ == "__main__":
    install_environment_variables()
    while True:
        try:
            run_cycle()
        except Exception as e:
            # Catch all "normal" errors and don't crash. Do log though.
            logging.error(f"Couldn't run triggerer cycle: {repr(e)}")

        time.sleep(60 * 15)
