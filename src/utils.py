import uuid
from datetime import datetime
import pytz

def generate_unique_string(length:int=8) -> str:
    unique_string = str(uuid.uuid4()).replace("-","")
    return unique_string[:length]



# Function to convert UTC to IST
def ist_datetime_current(utc_datetime_str=None):
    # If no input is provided, use current UTC time
    if utc_datetime_str is None:
        utc_datetime = datetime.utcnow()
    else:
        # Parse UTC datetime string to datetime object
        utc_datetime = datetime.strptime(utc_datetime_str, "%Y-%m-%d %H:%M:%S")

    # Define UTC timezone
    utc_timezone = pytz.timezone('UTC')

    # Set UTC timezone to the datetime object
    utc_datetime = utc_timezone.localize(utc_datetime)

    # Define IST timezone
    ist_timezone = pytz.timezone('Asia/Kolkata')

    # Convert to IST
    ist_datetime = utc_datetime.astimezone(ist_timezone)

    return ist_datetime
