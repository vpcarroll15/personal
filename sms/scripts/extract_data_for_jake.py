import os

from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

load_dotenv("/home/ubuntu/environment.env")


def postgres_to_csv(query, output_file, host, database, user, password, port=5432):
    """
    Execute PostgreSQL query and save results to CSV file.

    Parameters:
    query (str): SQL query to execute
    output_file (str): Path to save the CSV file
    host (str): Database host address
    database (str): Database name
    user (str): Database user
    password (str): Database password
    port (int): Database port (default: 5432)

    Returns:
    bool: True if successful, False otherwise
    """
    try:
        conn_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        print(f"Connecting to database: {conn_string}")

        engine = create_engine(conn_string)

        df = pd.read_sql_query(query, engine)
        df.to_csv(output_file, index=False)

        return True

    except Exception as e:
        print(f"Error: {str(e)}")
        return False


if __name__ == "__main__":
    db_params = {
        "host": os.environ["RDS_HOSTNAME"],
        "database": os.environ["RDS_DB_NAME"],
        "user": os.environ["RDS_USERNAME"],
        "password": os.environ["RDS_PASSWORD"],
        "port": os.environ["RDS_PORT"],
    }

    query = """
    SELECT
        sms_question.text AS question_text,
        sms_datapoint.updated_at AS updated_at,
        score,
        sms_datapoint.text AS response_text
    FROM (
        (sms_datapoint INNER JOIN sms_user ON sms_user.id = sms_datapoint.user_id)
        INNER JOIN sms_question ON sms_question.id = sms_datapoint.question_id)
    WHERE phone_number = '+18001234567' AND score IS NOT NULL
    ORDER BY sms_datapoint.updated_at
    """

    postgres_to_csv(query=query, output_file="output.csv", **db_params)
