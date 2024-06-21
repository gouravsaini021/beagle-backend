from fastapi import APIRouter,HTTPException,Request,BackgroundTasks,Depends
import asyncio
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import  AsyncSession

from src.utils import ist_datetime_current,generate_unique_string
from src.s3 import clean_file,upload_to_azure
from src.db import get_db,SoftUpload

router = APIRouter(tags=["Soft Upload"])

BLOCKED_BIN_FOR_UNIQUE_ID=["BFEBFBFF000206A7FEDV65BG23WEM2DXS7RFRHA0M6R8Z3W2VMVYX6QE3RRRATKW6Y90"]

async def upload_to_process_server(softupload_id,content):
    from src import BACKEND_SERVER_URL
    try:
        async with httpx.AsyncClient() as client:
            url=f"{BACKEND_SERVER_URL}/process"
            params = {"softupload_id": softupload_id}
            response=await client.post(url,params=params,files={"file": content})
    except Exception as e:
        raise

@router.post("/beaglesoftupload")
async def beaglesoftupload(request: Request,background_tasks:BackgroundTasks,db: AsyncSession = Depends(get_db)):
 
    data = await request.body()
    content_type_header = request.headers.get("Content-Type")
    unique_id=request.headers.get("UniqueId")
    release_version=request.headers.get("ReleaseVer")
    try:
        endswith,content=clean_file(data,content_type_header)
    except Exception as e:
         endswith,content="bin",data
    if unique_id in BLOCKED_BIN_FOR_UNIQUE_ID and endswith=='bin':
        return
    if not content:
        return
    filename=generate_unique_string(12) + "." + endswith
    
    file_link=upload_to_azure(content=content,filepath=filename)
    
    client_ip = request.client.host if request.client else None

    softupload = SoftUpload(
        ip=client_ip,
        content_type=content_type_header,
        unique_id=unique_id,
        release_version=release_version,
        file_path=filename,
        file_extension=endswith,
        file_link=file_link
    )

    async with db.begin():
        db.add(softupload)
        await db.commit()
        softupload_id=softupload.id
    
    background_tasks.add_task(upload_to_process_server,softupload_id,content)   #it will run in background.
    
    return {"id":softupload_id,"ip":client_ip}