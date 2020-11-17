"""
The types used by manager_main.py.

This will strongly resemble what is defined in sms/models.py, but without
dependencies on Django or web stuff. We will often serialize into or
deserialize from these classes.
"""
import dateutil


class Question:
    def __init__(self, serialized_dict):
        self.id = serialized_dict["id"]
        self.text = serialized_dict["text"]


class User:
    def __init__(self, serialized_dict):
        self.id = serialized_dict["id"]
        self.phone_number = serialized_dict["phone_number"]
        self.send_message_at_time = dateutil.parser.parse(serialized_dict["send_message_at_time"])
        self.questions = [Question(serialized_question) for serialized_question in serialized_dict["questions"]]
        self.start_text_hour = serialized_dict["start_text_hour"]
        self.end_text_hour = serialized_dict["end_text_hour"]
        self.timezone = serialized_dict["timezone"]
        self.text_every_n_days = serialized_dict["text_every_n_days"]
