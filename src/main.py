from fastapi import FastAPI,HTTPException,Request
import asyncio
from fastapi.responses import JSONResponse
from typing import List
from contextlib import asynccontextmanager
from databases import Database
from .db import initialize_tables,DB
from .schema import CreateItems,CreateStores,Receipt,ReceiptImage,OrganiseReceipt
from src import OPENAI_API_KEY
from src.utils import generate_unique_string,ist_datetime_current
import pymysql
from fastapi.staticfiles import StaticFiles
import base64
import os
from openai import OpenAI
import json
from fastapi.middleware.cors import CORSMiddleware
from .s3 import upload_to_s3,clean_file


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await DB.connect()
    await initialize_tables(DB)
    yield
    await DB.disconnect()

    

app=FastAPI(lifespan=lifespan)
app.mount("/files",StaticFiles(directory="files"),name="files")
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


@app.get("/receipts")
async def get_receipts():
    rv=[]
    receipts = await DB.fetch_all("select * from Receipt")
    for rec in receipts:
        receipt=dict(rec._mapping)
        items=await DB.fetch_all("select * from ReceiptItems where receipt_id=:receipt_id order by idx",values={'receipt_id':receipt['receipt_id']})
        it=get_mapping(items)
        receipt['items']=it
        rv.append(receipt)
    return rv

@app.get("/stores")
async def get_stores():
    stores = await DB.fetch_all("select * from Store ;")
    return get_mapping(stores)

@app.get("/items")
async def get_items():
    items = await DB.fetch_all("select * from Item ;")
    return get_mapping(items)

@app.get("/show_receipt_images")
async def show_receipt_image():
    receipts = await DB.fetch_all("select * from File where sub_folder='receipts' ")
    return receipts

async def create_receipt_items(items):

    if "item_code" not in items:
        items['item_code']=None
        items['item_name']=None

    if items['item_code']:
        items['item_name']=None
        item_details=await DB.fetch_one("select * from Item where item_code=:item_code",values={'item_code':items['item_code']})
        if item_details:
            items['item_name']=item_details._mapping['item_name']
        else:
            raise HTTPException(status_code=400,detail="Invalid item_code "+items['item_code'])
    
    while True:
        try:
            items['name']=generate_unique_string(10)
            await DB.execute("INSERT INTO ReceiptItems (name,idx,bill_item_name,item_code,item_name,price,mrp,qty,amount,receipt_id) VALUES (:name,:idx,:bill_item_name,:item_code,:item_name,:price,:mrp,:qty,:amount,:receipt_id)", values=items)
            break
        except pymysql.IntegrityError as e:
            items['name']=generate_unique_string(10)


async def create_receipt(receipt:Receipt):
    try:
        async with DB.transaction():
            rec=receipt.model_dump()
            rec['store_name']=None
            rec_items=rec['receipt_items']
            if rec['store_id']:
                store_data=await DB.fetch_one("select store_id,store_name from Store where Store.store_id= :store_id",values={'store_id':rec['store_id']})
                if store_data:
                    rec['store_name']=store_data._mapping['store_name']
                else:
                    raise HTTPException(status_code=400,detail="Invalid store_id "+rec['store_id'])

            if rec_items:
                del rec['receipt_items']
                id = await DB.execute("INSERT INTO Receipt (posting_date,posting_time,store_bill_no,receipt_store_name,total_amount,store_id,store_name,address) VALUES (:posting_date,:posting_time,:store_bill_no,:receipt_store_name,:total_amount,:store_id,:store_name,:address)", values=rec)
                for count,ele in enumerate(rec_items):
                    ele['idx']=count+1
                    ele['receipt_id']=id
                    await create_receipt_items(items=ele)
                return 
        raise HTTPException(status_code=400,detail='receipt_items is null for '+str(rec))
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))


@app.post("/post_receipts")
async def create_receipts(receipts:List[Receipt]):
    for receipt in receipts:
         await create_receipt(receipt=receipt)
    return JSONResponse(content="Success", status_code=201)
    

@app.post("/post_items")
async def create_item(items: CreateItems):
    values=items.model_dump()['items']
    try:
        async with DB.transaction():
            await DB.execute_many("INSERT INTO Item (item_code,item_name,category,brand,barcode,mrp) VALUES (:item_code,:item_name,:category,:brand,:barcode,:mrp)", values)
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    response_content={'message':'Items sucessfully created','items':values}
    return JSONResponse(content=response_content, status_code=201)

@app.post("/post_stores")
async def create_stores(stores: CreateStores):
    values=stores.model_dump()['stores']
    try:
        async with DB.transaction():
            await DB.execute_many("INSERT INTO Store (store_id,store_name,address,city,state,pincode,country,latitude,longitude) VALUES (:store_id,:store_name,:address,:city,:state,:pincode,:country,:latitude,:longitude)", values)
    except Exception as e:
        raise HTTPException(status_code=400,detail=str(e))
    response_content={'message':'Stores sucessfully created','items':values}
    return JSONResponse(content=response_content, status_code=201)

@app.post('/upload_receipt_image')
async def upload_file(images: ReceiptImage):
    decoded_data=base64.b64decode(images.image_data)
    image_type=images.image_type.split("/")[-1]
    image_name=generate_unique_string()+"."+image_type

    async def save_image(decoded_data,image_type,image_name):
        folder,subfolder="files","receipts"
        file_path=os.path.join(folder,subfolder, image_name)
        with open(file_path, "wb") as f:
            f.write(decoded_data)
        image_link="/files/"+subfolder+"/"+image_name
        values={"file_name":image_name,"link":image_link,"folder":folder,"sub_folder":subfolder}
        async with DB.transaction():
            id=await DB.execute("INSERT INTO File (file_name,link,folder,sub_folder) VALUES (:file_name,:link,:folder,:sub_folder)", values=values)
        
        return {"id":id,"image_link":image_link}
    
    async def process_receipt(base64_image):
        system_prompt = "Extract and format all relevant fields from the following receipt image."
        messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image}"}
                    ]
                }
            ]
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=messages,
            max_tokens=1000
        )
        return {"text": response.choices[0].message.content}
    
    try:
        result = await asyncio.gather(save_image(decoded_data=decoded_data,image_type=image_type,image_name=image_name),process_receipt(base64_image=images.image_data),return_exceptions=False)
        return JSONResponse(content=result, status_code=201)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.post("/organize_receipt")
async def organize_receipt(req: OrganiseReceipt):
    text=req.text
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": """You are a helpful assistant designed to output JSON.you will give me field as item_name or item ( Predict the item_name from the abbreviated name and return the full name. DO NOT MAKE UP NAMES YOURSELF.),qty,mrp,price,total amount,barcode or Bcode,amount,date(yyyy-mm-dd),time store_name,address,gstin,total_qty,total_items,final_amount,bill or receipt id,gstin ,user name,phone no , email feel free to leave the field empty if you cann't find field and if you find extra field plese add to json.i am also adding sample expection written below
 {
  "store_name": "FRESH MART",
  "address": "#1174, 24th Main Road, Near Maranmma Temple, Parangi Pallya, HSR Layout, 2nd Sector, Bangalore - 560102",
  "gstin": "29BCBPA3750R1ZB",
  "bill_id": "77497",
  "user_name": "Ashok",
  "date": "2024-01-30",
  "total_qty": 3,
  "total_amount": 123.00,
  "items": [
    {
      "item_name": "POTATO",
      "qty": 2.070,
      "mrp": null,
      "price": 25.90,
      "amount": 53.61,
      "barcode": null
    },
    {
      "item_name": "CARROT OOTY",
      "qty": 0.328,
      "mrp": null,
      "price": 79.00,
      "amount": 26.21,
      "barcode": null
    },
    {
      "item_name": "CAPSICUM HYBRID",
      "qty": 0.248,
      "mrp": null,
      "price": 74.90,
      "amount": 18.68,
      "barcode": null
    },
    {
      "item_name": "CABBAGE MEDIUM",
      "qty": 0.498,
      "mrp": null,
      "price": 31.90,
      "amount": 15.89,
      "barcode": null
    },
    {
      "item_name": "BEANS RINGS ROUND",
      "qty": 0.076,
      "mrp": null,
      "price": 119.90,
      "amount": 9.11,
      "barcode": null
    }
  ]
}
"""},
            {"role": "user", "content": text}
        ]
    )
    try:
        organized_data = response.choices[0].message.content
        return JSONResponse(content=json.loads(organized_data), status_code=201)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/create_receipt_from_image_json")
async def create_receipt_from_json(receipt:dict,file_id:int):

    values={"posting_date":None,"posting_time":None,"store_bill_no":None,"receipt_store_name":None,"total_amount":None,"gstin":None,"address":None,"json_from_image":json.dumps(receipt)}
    if "text_from_image" not in receipt:
        raise HTTPException(status_code=400, detail="Cannot find text_from_image field")
    else:
        values["text_from_image"]=receipt["text_from_image"]
    if "store_name" in receipt:
        values["receipt_store_name"]=receipt["store_name"]
    if "bill_id" in receipt:
        values["store_bill_no"]=receipt["bill_id"]
    if "gstin" in receipt:
        values["gstin"]=receipt["gstin"]
    if "address" in receipt:
        values["address"]=receipt["address"]
    if "total_amount" in receipt:
        values["total_amount"]=receipt["total_amount"]
    if "date" in receipt:
        values["posting_date"]=receipt["date"]
    if "time" in receipt:
        values["posting_time"]=receipt["time"]
    receipt_items=[]  
    for item in receipt["items"]:
        receipt_item={}
        if "item_name" in item:
            receipt_item["bill_item_name"]=item["item_name"]
        if "qty" in item:
            receipt_item["qty"]=item["qty"]
        if "price" in item:
            receipt_item["price"]=item["price"]
        if "amount" in item:
            receipt_item["amount"]=item["amount"]
        else:
            try:
                receipt_item["amount"]=receipt_item["qty"]*receipt_item["price"]
            except Exception:
                pass
        if "mrp"in item:
            receipt_item["mrp"]=item["mrp"]
        receipt_items.append(receipt_item)
    try:
        async with DB.transaction():
            receipt_id = await DB.execute("INSERT INTO Receipt (posting_date,posting_time,store_bill_no,receipt_store_name,total_amount,gstin,address,text_from_image,json_from_image) VALUES (:posting_date,:posting_time,:store_bill_no,:receipt_store_name,:total_amount,:gstin,:address,:text_from_image,:json_from_image)", values=values)
            await DB.execute("UPDATE File set receipt_id=:receipt_id where id=:id",values={"id":file_id,"receipt_id":receipt_id})
            for count,ele in enumerate(receipt_items):
                        ele['idx']=count+1
                        ele['receipt_id']=receipt_id
                        await create_receipt_items(items=ele)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content="successfull", status_code=201)

@app.delete("/stores")
async def delete_stores():
    try:
        async with DB.transaction():
            await DB.execute("Delete from Store;")
        return JSONResponse(content="successfully delete store data", status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    
@app.delete("/item")
async def delete_item():
    try:
        async with DB.transaction():
            await DB.execute("Delete from Item;")
            return JSONResponse(content="successfully delete item data", status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    

@app.post('/upload_receipt_image_with_id')
async def upload_file_with_id(images: ReceiptImage,receipt_id:int):
    decoded_data=base64.b64decode(images.image_data)
    image_type=images.image_type.split("/")[-1]
    image_name=str(receipt_id)+"_"+generate_unique_string()+"."+image_type

    async def save_image(decoded_data,image_name,receipt_id):
        folder,subfolder="files","receipts"
        file_path=os.path.join(folder,subfolder, image_name)
        with open(file_path, "wb") as f:
            f.write(decoded_data)
        image_link="/files/"+subfolder+"/"+image_name
        values={"file_name":image_name,"link":image_link,"folder":folder,"sub_folder":subfolder,"receipt_id":receipt_id}
        async with DB.transaction():
            id=await DB.execute("INSERT INTO File (file_name,link,folder,sub_folder,receipt_id) VALUES (:file_name,:link,:folder,:sub_folder,:receipt_id)", values=values)
        
        return {"id":id,"image_link":image_link}
    try:
        result = await save_image(decoded_data=decoded_data,image_name=image_name,receipt_id=receipt_id)
        return JSONResponse(content=result, status_code=201)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))

@app.post("/beaglesoftupload")
async def beaglesoftupload(request: Request):
 
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
    
    client_ip = request.client.host
    current_time=ist_datetime_current()
    values={"ip":client_ip,"creation":current_time,"content_type":content_type_header,"unique_id":unique_id,"release_version":release_version,"file_path":filename,"file_extension":endswith,"file_link":file_link}
    try:
        async with DB.transaction():
                id=await DB.execute("INSERT INTO SoftUpload (ip,creation,content_type,unique_id,release_version,file_path,file_extension,file_link) VALUES (:ip,:creation,:content_type,:unique_id,:release_version,:file_path,:file_extension,:file_link)", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return {"id":id,"ip":client_ip}

@app.get("/get_beaglesoftupload")
async def get_beaglesoftupload():
    soft_upload = await DB.fetch_all("select * from SoftUpload order by id desc limit 10;")
    return soft_upload

@app.get("/get_beaglesoftupload_with_id")
async def get_beaglesoftupload_with_id(id:int):
    values={"id":id}
    soft_upload = await DB.fetch_one("select * from SoftUpload where id=:id",values=values)
    return soft_upload

@app.get("/get_beaglesoftupload_with_unique_id")
async def get_beaglesoftupload_with_unique_id(unique_id:str,n:int=1):
    """Fetches the last `n` records from `SoftUpload` table for a given `unique_id`."""
    if n < 1:
        raise HTTPException(status_code=400, detail="Parameter n must be at least 1.")

    values={"unique_id":unique_id,"n":n}
    soft_upload = await DB.fetch_all("select * from SoftUpload where file_extension='SPL' and unique_id=:unique_id order by creation desc limit :n",values=values)

    return soft_upload

@app.post("/Print2waUpload")
async def Print2waUpload(request: Request):
 
    data = await request.body()
    content_type_header = request.headers.get("Content-Type")
    timestamp=request.headers.get("Timestamp")
    phone_number=request.headers.get("PhoneNumber")
    device_id=request.headers.get("DeviceId")
    release_version=request.headers.get("ReleaseVersion")
    try:
        endswith,content=clean_file(data,content_type_header)
    except Exception as e:
         endswith,content=".bin",data
    file_path="pdf/" + generate_unique_string(12) + "." + endswith

    upload_to_s3(content=content,filename=file_path)
    file_link="https://beaglebucket.s3.amazonaws.com/" + file_path
    
    client_ip = request.client.host
    current_time=ist_datetime_current()
    values={"ip":client_ip,"creation":current_time,'timestamp':timestamp,'phone_number':phone_number,'device_id':device_id,'release_version':release_version,'file_link':file_link,'file_path':file_path,'file_extension':endswith,"content_type":content_type_header}
    try:
        async with DB.transaction():
                id=await DB.execute("INSERT INTO Print2wa (ip,creation,timestamp,phone_number,device_id,release_version,file_link,file_path,file_extension,content_type) VALUES (:ip,:creation,:timestamp,:phone_number,:device_id,:release_version,:file_link,:file_path,:file_extension,:content_type)", values=values)
    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))
    return {"id":id,"ip":client_ip}