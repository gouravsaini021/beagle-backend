from fastapi import FastAPI,HTTPException,Request,File, UploadFile
import asyncio
from fastapi.responses import JSONResponse
from typing import List
from contextlib import asynccontextmanager
from databases import Database
from .db import initialize_tables,DB
from src import OPENAI_API_KEY
from src.utils import generate_unique_string,ist_datetime_current
import pymysql
from fastapi.staticfiles import StaticFiles
import base64
import os
from openai import OpenAI
import json
from fastapi.middleware.cors import CORSMiddleware
from src.api import softupload,print2wa
import sentry_sdk
from src.s3 import upload_to_azure

@asynccontextmanager
async def lifespan(_app: FastAPI):
    await DB.connect()
    await initialize_tables(DB)
    yield
    await DB.disconnect()

sentry_sdk.init(
    dsn="https://55c726ce37e4f6fa23de011c546731ad@o4507208886386688.ingest.us.sentry.io/4507208890253312",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    enable_tracing=True,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

    

app=FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["*"],  # Adjust this to the specific origins you want to allow
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

client = OpenAI(api_key=OPENAI_API_KEY)

def get_mapping(items):
    rv=[]
    for i in items:
        rv.append(i._mapping)
    return rv

@app.get("/sentry-debug")
async def trigger_error():
    division_by_zero = 1 / 0

@app.get("/heartbeat")
async def heartbeat(request: Request):
    unique_id=request.headers.get("UniqueId")
    release_version=request.headers.get("ReleaseVer")
    current_time=ist_datetime_current()
    client_ip = request.client.host if request.client else None
    values={"ip":client_ip,"creation":current_time,"unique_id":unique_id,"release_version":release_version}
    try:
        async with DB.transaction():
                id=await DB.execute("INSERT INTO Heartbeat (ip,creation,unique_id,release_version) VALUES (:ip,:creation,:unique_id,:release_version)", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return "ok"

@app.post("/heartbeat")
async def post_heartbeat(request:Request,file: UploadFile = File(...)):
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
    current_time=ist_datetime_current()

    values={
         "ip":client_ip,
         "creation":current_time,
         "unique_id":unique_id,
         "release_version":release_version,
         "file_path":filename,
         "file_extension":extension[1:],
         "file_link":file_link
         }
    try:
        async with DB.transaction():
            id=await DB.execute("INSERT INTO HeartbeatUpload (ip,creation,unique_id,release_version,file_path,file_extension,file_link) VALUES (:ip,:creation,:unique_id,:release_version,:file_path,:file_extension,:file_link)", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return {"id":id,"ip":client_ip}


app.include_router(softupload.router)
app.include_router(print2wa.router)