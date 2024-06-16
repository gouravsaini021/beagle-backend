from fastapi import FastAPI,HTTPException,Request,APIRouter
from typing import Dict,Union,Optional

from src.db import DB
from src.utils import generate_unique_string,ist_datetime_current
from src.s3 import upload_to_azure

router=APIRouter(tags=["Print2waUpload"])

@router.post('/Print2waUpload',response_model=Dict[str, Union[str, int, None]])
async def Print2waUpload(request: Request) -> Dict[str, Union[str, int, None]]:
    content = await request.body()
    endswith="pdf"
    content_type_header = request.headers.get("Content-Type")
    timestamp=request.headers.get("Timestamp")
    phone_number=request.headers.get("PhoneNumber")
    device_id=request.headers.get("DeviceId")
    release_version=request.headers.get("ReleaseVersion")
    file_path="pdf/" + generate_unique_string(12) + "." + endswith

    file_link=upload_to_azure(content=content,filepath=file_path)
    
    client_ip: Optional[str] = request.client.host if request.client else None
    current_time=ist_datetime_current()
    values={
        'ip':client_ip,
        'creation':current_time,
        'timestamp':timestamp,
        'phone_number':phone_number,
        'device_id':device_id,
        'release_version':release_version,
        'file_link':file_link,
        'file_path':file_path,
        'file_extension':endswith,
        'content_type':content_type_header
        }
    try:
        async with DB.transaction():
                id=await DB.execute("""
                    INSERT INTO Print2wa (
                        ip,creation,timestamp,phone_number,device_id,
                        release_version,file_link,file_path,file_extension,content_type
                    ) VALUES (
                    :ip,:creation,:timestamp,:phone_number,:device_id,
                    :release_version,:file_link,:file_path,:file_extension,:content_type
                    )""", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return {"id":id,"ip":client_ip}