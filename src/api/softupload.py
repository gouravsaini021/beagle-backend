from fastapi import APIRouter,HTTPException,Request,BackgroundTasks
import asyncio

from src.utils import ist_datetime_current,generate_unique_string
from src.db import DB
from src.s3 import clean_file,upload_to_s3
from src.api.background_job import background_task_for_softupload

router = APIRouter(tags=["Soft Upload"])


@router.post("/beaglesoftupload")
async def beaglesoftupload(request: Request,background_tasks:BackgroundTasks):
 
    data = await request.body()
    content_type_header = request.headers.get("Content-Type")
    unique_id=request.headers.get("UniqueId")
    release_version=request.headers.get("ReleaseVer")
    try:
        endswith,content=clean_file(data,content_type_header)
    except Exception as e:
         endswith,content=".bin",data
    filename=generate_unique_string(12) + "." + endswith

    upload_to_s3(content=content,filename=filename)
    file_link="https://beaglebucket.s3.amazonaws.com/" + filename
    
    client_ip = request.client.host if request.client else None
    current_time=ist_datetime_current()
    values={
         "ip":client_ip,
         "creation":current_time,
         "content_type":content_type_header,
         "unique_id":unique_id,
         "release_version":release_version,
         "file_path":filename,
         "file_extension":endswith,
         "file_link":file_link
         }
    try:
        async with DB.transaction():
                id=await DB.execute("INSERT INTO SoftUpload (ip,creation,content_type,unique_id,release_version,file_path,file_extension,file_link) VALUES (:ip,:creation,:content_type,:unique_id,:release_version,:file_path,:file_extension,:file_link)", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
    background_tasks.add_task(background_task_for_softupload,id,content)   #it will run in background.
    
    return {"id":id,"ip":client_ip}

@router.get("/get_beaglesoftupload")
async def get_beaglesoftupload():
    soft_upload = await DB.fetch_all("select * from SoftUpload order by id desc limit 2000 ;")
    return soft_upload

@router.get("/get_beaglesoftupload_with_id")
async def get_beaglesoftupload_with_id(id:int):
    values={"id":id}
    soft_upload = await DB.fetch_one("select * from SoftUpload where id=:id",values=values)
    return soft_upload

@router.get("/get_beaglesoftupload_with_unique_id")
async def get_beaglesoftupload_with_unique_id(unique_id:str,n:int=1):
    """Fetches the last `n` records from `SoftUpload` table for a given `unique_id`."""
    if n < 1:
        raise HTTPException(status_code=400, detail="Parameter n must be at least 1.")

    values={"unique_id":unique_id,"n":n}
    soft_upload = await DB.fetch_all("select * from SoftUpload where file_extension='SPL' and unique_id=:unique_id order by creation desc limit :n",values=values)

    return soft_upload

@router.get("/get_processed_receipt")
async def get_processed_receipt(id:int):
    """Fetches record from `ProcessReceipt` table for a given `id`."""
    
    values={"id":id}
    process_receipt = await DB.fetch_all("select * from ProcessedReceipt where id=:id ",values=values)

    return process_receipt

@router.get("/get_fmcg_data")
async def get_fmcg_data(id:int):
    """Fetches record from `FMCG_master` table for a given `id`."""
    values={"id":id}
    fmcg_data = await DB.fetch_all("select * from FMCG_Master where id=:id ",values=values)
    return fmcg_data

@router.get("/get_spl_by_tag")
async def get_spl_by_tag(tag:str,unique_id:str):
    """
    Fetches SPL file from the `SoftUpload` table based on a given `tag` and unique_id.
    
    Args:
        tag (str): The tag to filter soft uploads.

    Returns:
        List[Dict]: A list of dictionaries representing soft uploads.
    """
    values={"tag":tag, "unique_id":unique_id}

    soft_upload = await DB.fetch_all("""
        SELECT su.*
        FROM SoftUpload AS su
        JOIN TagSoftUpload AS tsu ON tsu.softupload_id = su.id
        WHERE file_extension = 'SPL' AND tsu.type = :tag and su.unique_id:unique_id
        ORDER BY su.creation DESC
    """,values=values)

    return soft_upload