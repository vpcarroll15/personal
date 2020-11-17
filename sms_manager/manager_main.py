from datetime import datetime, timezone
import logging
import time

from types import Question, User
from api_client import RestApiClient


def set_next_contact_time(user, api_client):
    pass


def send_sms_and_create_data_point(user, api_client):
    pass


def run_cycle():
    # 1) Get the list of users.
    api_client = RestApiClient()
    serialized_users = api_client.invoke("sms/users")
    users = [User(serialized_user) for serialized_user in serialized_users]

    for user in users:
        if user.send_message_at_time < datetime.now(tz=timezone.utc):
            # Set the next contact time FIRST, so that we don't spam Twilio if something goes
            # wrong with this request.
            set_next_contact_time(user, api_client)
            send_sms_and_create_data_point(user, api_client)


if __name__ == "__main__":
    while True:
        try:
            run_cycle()
        except Exception as e:
            # Catch all "normal" errors and don't crash. Do log though.
            logging.error(repr(e))

        time.sleep(60 * 15)
