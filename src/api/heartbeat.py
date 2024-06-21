from fastapi import APIRouter,HTTPException,Request,BackgroundTasks,Depends,UploadFile,File
from fastapi.responses import JSONResponse
import os
import asyncio
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import  AsyncSession

from src.utils import ist_datetime_current,generate_unique_string
from src.s3 import clean_file,upload_to_azure
from src.db import get_db,Heartbeat,HeartbeatUpload

router = APIRouter(tags=["Heartbeat"])

@router.get("/heartbeat")
async def heartbeat(request: Request,db: AsyncSession = Depends(get_db)):
    unique_id=request.headers.get("UniqueId")
    release_version=request.headers.get("ReleaseVer")
    current_time=ist_datetime_current()
    client_ip = request.client.host if request.client else None
    heartbeat=Heartbeat(
        ip=client_ip,
        creation=current_time,
        unique_id=unique_id,
        release_version=release_version

    )
    try:
        async with db.begin():
            db.add(heartbeat)
            await db.commit()
    except Exception as e:
         raise HTTPException(status_code=500,detail=str(e))
    return "ok"

@router.post("/heartbeat")
async def post_heartbeat(request:Request,file: UploadFile = File(...),db: AsyncSession = Depends(get_db)):
    # Check if the file was uploaded
    if not file:
        return JSONResponse(status_code=400, content={"message": "No file provided"})
    unique_id=request.headers.get("UniqueId")
    release_version=request.headers.get("ReleaseVer")
    # Here, you can process the uploaded file
    content = await file.read()
    _, extension = os.path.splitext(str(file.filename))
    filename="heartbeat/"+generate_unique_string(12) + extension
    file_link=upload_to_azure(content=content,filepath=filename)
    client_ip = request.client.host if request.client else None
    heartbeat=HeartbeatUpload(
                creation=ist_datetime_current(),
                ip=client_ip,
                unique_id=unique_id,
                release_version=release_version,
                file_path=filename,
                file_extension=extension[1:],
                file_link=file_link
                )
    try:
        async with db.begin():
            db.add(heartbeat)
            await db.commit()
            id=heartbeat.id
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    return {"id":id,"ip":client_ip}