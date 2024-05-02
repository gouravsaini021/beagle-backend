from typing import Optional, Tuple , Union
import requests
import asyncio

from src.utils import ist_datetime_current
from src.db import DB
from src.s3 import upload_to_s3


async def process_receipt(id:int,file_content:bytes) -> Union[Tuple[int, str], Tuple[bool, bool] , Tuple[int,None]]:
    """
    Process a receipt file asynchronously.

    Args:
        id (int): The ID of the SoftUpload Table.
        file_content (bytes): The content of the receipt file.

    Returns:
        Union[Tuple[int, str], Tuple[bool, bool], Tuple[int, None]]: A tuple containing processed information or status.
    """

    current_time=ist_datetime_current()

    # Initial values for database insertion
    iv={"creation":current_time,"modified":current_time,"softupload_id":id,"image_link":None,"image_path":None,'is_processed':0,"processed_text":None}
    
    async def convert_to_image():
        """
        Convert XPS file to PNG image and upload to S3.
        """
        url="https://converter.beaglenetwork.com/xps2png"
        response=requests.post(url, files={"file": file_content})
        if response.status_code == 200:
            filename=f"{id}.png"
            image_path="processed_images/"+filename
            image_link='https://beaglebucket.s3.amazonaws.com/'+image_path
            # Upload to S3
            upload_to_s3(response.content,image_path)
            iv["image_link"]=image_link
            iv["image_path"]=image_path

    async def extract_text():
        """
        Extract text from XPS file.
        """
        url="https://converter.beaglenetwork.com/xps2txt"
        response = requests.post(url, files={"file": (f"{id}.xps",file_content)})
        if response.status_code == 200:
            if len(response.text)<5:
                text_from_xps=response.text
                iv['processed_text']=text_from_xps
                iv['is_processed']=1
    
    try:
        result = await asyncio.gather(convert_to_image(),extract_text(),return_exceptions=False)
    except Exception as e:
        raise e
    
    # If either image link or processed text is available, insert into the database
    if iv["image_link"] or iv["processed_text"]:
        async with DB.transaction():
            id=await DB.execute("INSERT INTO ProcessedReceipt (creation,modified,softupload_id,image_link,image_path,is_processed,processed_text) VALUES (:creation,:modified,:softupload_id,:image_link,:image_path,:is_processed,:processed_text)", values=iv)

    if iv["processed_text"]:
         return (id,iv["processed_text"])
    
    return (False,False)
    
    

    

