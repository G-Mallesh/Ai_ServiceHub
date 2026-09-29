import os
from dotenv import load_dotenv

load_dotenv()


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "ai-service-hub-secret-key"
    )

    MYSQL_HOST = os.getenv(
        "DB_HOST",
        "localhost"
    )

    MYSQL_PORT = int(os.getenv(
        "DB_PORT",
        "3306"
    ))

    MYSQL_USER = os.getenv(
        "DB_USER",
        "root"
    )

    MYSQL_PASSWORD = os.getenv(
        "DB_PASSWORD",
        "root"
    )

    MYSQL_DATABASE = os.getenv(
        "DB_NAME",
        "ai_service_hub"
    )

    GOOGLE_MAPS_API_KEY = os.getenv(
        "GOOGLE_MAPS_API_KEY",
        ""
    )

    RAZORPAY_KEY_ID = os.getenv(
        "RAZORPAY_KEY_ID",
        "rzp_test_TeJXdHbtvbZsNd"
    )

    RAZORPAY_KEY_SECRET = os.getenv(
        "RAZORPAY_KEY_SECRET",
        "jjONV0WW5UEyplYbNt2noobI"
    )