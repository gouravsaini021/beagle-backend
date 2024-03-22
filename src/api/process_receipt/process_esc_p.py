from typing import Optional, Tuple , Union

from src.utils import ist_datetime_current
from src.db import DB



def is_utf8(byte):
    """Check if a byte is a valid UTF-8 character."""
    try:
        bytes([byte]).decode('utf-8')
        # byte.decode('utf-8')
        return True
    except UnicodeDecodeError:
        return False

def replace_non_utf8_with_space(byte):
    if is_utf8(byte):
        return bytes([byte]).decode('utf-8')
    else:
        return ''
    
async def process_receipt(id:int,file_content:bytes) -> Union[Tuple[int, str], Tuple[bool, bool]]:
    processed_text=""
    for i in file_content:
        processed_text+=replace_non_utf8_with_space(i)
    current_time=ist_datetime_current()
    iv={"creation":current_time,"modified":current_time,"soft_upload_id":id,'is_processed':1,"processed_text":processed_text}

    async with DB.transaction():
            id=await DB.execute("INSERT INTO ProcessedReceipt (creation,modified,soft_upload_id,is_processed,processed_text) VALUES (:creation,:modified,:soft_upload_id,:is_processed,:processed_text)", values=iv)

    return (id,processed_text)

