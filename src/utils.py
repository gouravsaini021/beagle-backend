import uuid
from datetime import datetime
import pytz

def generate_unique_string(length:int=8) -> str:
    unique_string = str(uuid.uuid4()).replace("-","")
    return unique_string[:length]



def ist_datetime_current():
   """ Get current time of 'Asia/kolkata time zone. """
   timezone = pytz.timezone('Asia/Kolkata')
   kolkata_time = datetime.now(timezone)
   # MySQL DATETIME format with microseconds
   return kolkata_time.strftime('%Y-%m-%d %H:%M:%S.%f')
