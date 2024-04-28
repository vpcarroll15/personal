"""
The main logic that drives sending of daily goals to users.

This should remain fairly compact, and complicated logic should be pushed to helper libraries.
"""

import logging
import os
import time

from twilio.rest import Client as TwilioClient

from api_client import TwilioManagerApiClient
from platform_info import install_environment_variables
from daily_goals_app_types import User


def set_last_start_text_sent_date(user: User, api_client: TwilioManagerApiClient):
    logging.info(f"Setting last start text sent date for user {user.id}")

    # Save this to the DB.
    user_date = user.now.date()
    api_client.invoke(
        "daily_goals/user",
        request_type="put",
        payload={"id": user.id, "last_start_text_sent_date": str(user_date)},
    )
    logging.info(
        f"Set last start text sent date for user {user.id} to date {user_date}"
    )


def send_sms_and_create_checkin(
    user: User,
    api_client: TwilioManagerApiClient,
    twilio_client: TwilioClient,
    twilio_phone_number: str,
):
    logging.info(f"Creating checkin for user {user.id}")

    api_client.invoke(
        "daily_goals/checkin",
        request_type="post",
        payload={"user_id": user.id, "possible_focus_areas": user.possible_focus_areas},
    )

    # Now that we have created the data point, let's send the SMS.
    logging.info(f"Sending SMS to user {user.id}")

    sms_body = "Choose some goals for today! Some defaults:\n\n"

    focus_area_strs = []
    for i, focus_area in enumerate(user.possible_focus_areas):
        # Make sure to 1-index the list for readability.
        focus_area_strs.append(f"{i + 1}. {focus_area}")
    sms_body += "\n".join(focus_area_strs)

    sms_body += (
        "\n\nReply with the numbers of the goals you want to focus on today, "
        "or write in your own. Comma-separate multiple goals. Your response must start with 'g'."
    )

    twilio_client.messages.create(
        from_=twilio_phone_number, body=sms_body, to=user.phone_number
    )


def run_cycle():
    # This will crash if these variables aren't found in our environment, which
    # is perfect.
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    twilio_phone_number = os.environ["TWILIO_DAILY_GOALS_APP_PHONE_NUMBER"]
    twilio_client = TwilioClient(account_sid, auth_token)

    api_client = TwilioManagerApiClient()
    serialized_users = api_client.invoke("daily_goals/users")
    users = [User(**serialized_user) for serialized_user in serialized_users["users"]]

    for user in users:
        if user.should_start_checkin:
            try:
                # Set the next contact time FIRST, so that we don't spam Twilio if something goes
                # wrong with this request.
                set_last_start_text_sent_date(user, api_client)
                send_sms_and_create_checkin(
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
            logging.error(f"Couldn't run Daily Goals manager cycle: {repr(e)}")

        time.sleep(60 * 15)
