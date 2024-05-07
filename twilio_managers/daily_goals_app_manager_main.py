"""
The main logic that drives sending of daily goals to users.

This should remain fairly compact, and complicated logic should be pushed to helper libraries.
"""

from datetime import timedelta
import logging
import os
import re
import time

from anthropic import Anthropic
from twilio.rest import Client as TwilioClient

from api_client import TwilioManagerApiClient
from platform_info import install_environment_variables
from daily_goals_app_types import DailyCheckin, User


# Let's use opus for now, just for fun.
AI_MODEL_TO_USE = "claude-3-opus-20240229"


SYSTEM_PROMPT: str = """
You are an AI assistant that suggests daily goals to users. Each suggestion should have these properties:

1. Between five and fifteen words.
2. Address exactly one topic. Don't try to combine multiple goals into the same suggestion.
3. Use the context provided by the user.
4. The goals should be creative and memorable.
5. The goals should be simply written. Don't use too many adjectives or adverbs.
6. Each goal should be placed within XML tags: <goal></goal>.
7. Goals shouldn't be inspirational. They should just be practical and thought-provoking.

Here are examples of good goals.

<goal>Be sweaty at the end of a workout in which you really push yourself.</goal>
<goal>Make dinner reservations somewhere that Grace doesn't expect.</goal>
<goal>Reach out to Norman and see what he's up to.</goal>

Here are examples of bad goals.

<goal>Embrace the unknown, fearlessly taking on new challenges.</goal> This goal is too wordy, vague, nonspecific, and inspirational.
<goal>Stretch your limits, unlocking flexibility and freedom. </goal> Same problem as above. Generic goals are bad.
<goal>Sculpt strength and endurance with fierce intensity.</goal> Wordy, poetic language is wrong.

When the user gives you context on who they are, use that information to suggest three good goals that obey the above rules.
"""


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

    sms_body = "Choose your focus for today. Some defaults:\n\n"

    focus_area_strs = []
    for i, focus_area in enumerate(user.possible_focus_areas):
        # Make sure to 1-index the list for readability.
        focus_area_strs.append(f"{i + 1}. {focus_area}")
    sms_body += "\n".join(focus_area_strs)

    sms_body += (
        "\n\nReply with the numbers of what you'd like to focus on today, "
        "or write in your own. Comma-separate multiple focus areas. Your response must start with 'g'."
    )

    twilio_client.messages.create(
        from_=twilio_phone_number, body=sms_body, to=user.phone_number
    )


def update_user_focus_areas(
    user: User, api_client: TwilioManagerApiClient, anthropic_client: Anthropic
) -> None:
    if user.possible_focus_areas:
        return

    if not user.ai_prompt:
        return

    # Fetch all the goals created in the past seven days for this user.
    serialized_checkins = api_client.invoke(
        resource="daily_goals/checkin",
        request_type="get",
        params={"user_id": user.id, "created_at__gte": user.now - timedelta(days=7)},
    )
    checkins = [
        DailyCheckin(**serialized_checkin)
        for serialized_checkin in serialized_checkins["checkins"]
    ]
    used_goals = [goal for checkin in checkins for goal in checkin.possible_focus_areas]

    used_goals_str = (
        "\n\nHere are goals that have been created recently for this user:\n\n"
    )
    for goal in used_goals:
        used_goals_str += f"<goal>{goal}</goal>\n"
    used_goals_str += "\nPlease do not reuse any of these goals. Try to create goals that are meaningfully different."

    adjusted_prompt = user.ai_prompt + used_goals_str

    response = anthropic_client.messages.create(
        model=AI_MODEL_TO_USE,
        max_tokens=1024,
        temperature=1,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": adjusted_prompt,
                    }
                ],
            },
        ],
    )

    pattern = r"<goal>(.*?)</goal>"
    goals = re.findall(pattern, response.content[0].text, re.DOTALL)
    user.possible_focus_areas = goals


def run_cycle():
    # This will crash if these variables aren't found in our environment, which
    # is perfect.
    account_sid = os.environ["TWILIO_ACCOUNT_SID"]
    auth_token = os.environ["TWILIO_AUTH_TOKEN"]
    twilio_phone_number = os.environ["TWILIO_DAILY_GOALS_APP_PHONE_NUMBER"]
    twilio_client = TwilioClient(account_sid, auth_token)

    api_client = TwilioManagerApiClient()
    anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    serialized_users = api_client.invoke("daily_goals/users")
    users = [User(**serialized_user) for serialized_user in serialized_users["users"]]

    for user in users:
        if user.should_start_checkin:
            try:
                # Use AI if necessary to update the user's focus areas.
                update_user_focus_areas(user, api_client, anthropic_client)
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
