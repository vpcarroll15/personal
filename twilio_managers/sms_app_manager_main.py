"""
The main logic that drives sending of SMS's to users.

This should remain fairly compact, and complicated logic should be pushed to helper libraries.
"""

from datetime import datetime, timezone, timedelta
import logging
import os
import random
import time

import pytz
from twilio.rest import Client as TwilioClient

from api_client import TwilioManagerApiClient
from platform_info import install_environment_variables
from twilio_managers.sms_app_types import User


def set_next_contact_time(user, api_client):
    logging.info(f"Setting next contact time for user {user.id}")

    # I hate timezones so much. Get the current time in the user's timezone.
    target_datetime = datetime.now(tz=timezone.utc).astimezone(
        pytz.timezone(user.timezone)
    )

    # Increment it.
    target_datetime += timedelta(days=user.text_every_n_days)

    # Choose an hour while we think the user will be awake.
    hour = random.randrange(user.start_text_hour, user.end_text_hour)
    minute = random.randrange(60)
    target_datetime = target_datetime.replace(hour=hour, minute=minute)

    # Save this to the DB.
    api_client.invoke(
        "sms/user",
        request_type="put",
        payload={"id": user.id, "send_message_at_time": target_datetime.isoformat()},
    )
    logging.info(
        f"Set next contact time for user {user.id} to time {target_datetime.isoformat()}"
    )


def send_sms_and_create_data_point(
    user, api_client, twilio_client, twilio_phone_number
):
    # First we create the DataPoint...just in case the user responds to our text really really fast. :)
    # There is also no cost to creating a DataPoint and never sending a text, if that fails.
    logging.info(f"Creating DataPoint for user {user.id}")

    question = random.choice(user.questions)
    api_client.invoke(
        "sms/data_point",
        request_type="post",
        payload={"user_id": user.id, "question_id": question.id},
    )

    # Now that we have created the data point, let's send the SMS.
    logging.info(f"Sending SMS to user {user.id}")

    sms_body = f"{question.text} ({question.min_score}-{question.max_score})"
    twilio_client.messages.create(
        from_=twilio_phone_number, body=sms_body, to=user.phone_number
    )


def run_cycle():
    # This will crash if these variables aren't found in our environment, which
    # is perfect.
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    twilio_phone_number = os.environ["TWILIO_SMS_APP_PHONE_NUMBER"]
    twilio_client = TwilioClient(account_sid, auth_token)

    api_client = TwilioManagerApiClient()
    serialized_users = api_client.invoke("sms/users")
    users = [User(serialized_user) for serialized_user in serialized_users["users"]]

    for user in users:
        if user.send_message_at_time < datetime.now(tz=timezone.utc):
            try:
                # Set the next contact time FIRST, so that we don't spam Twilio if something goes
                # wrong with this request.
                set_next_contact_time(user, api_client)
                send_sms_and_create_data_point(
                    user, api_client, twilio_client, twilio_phone_number
                )
            except Exception as e:
                # One bad user shouldn't break things for everyone.
                logging.error(f"User {user.id} couldn't be processed: {repr(e)}")


if __name__ == "__main__":
    install_environment_variables()
    while True:
        try:
            run_cycle()
        except Exception as e:
            # Catch all "normal" errors and don't crash. Do log though.
            logging.error(f"Couldn't run SMS manager cycle: {repr(e)}")

        time.sleep(60 * 15)
