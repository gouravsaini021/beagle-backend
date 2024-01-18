from fastapi import FastAPI,HTTPException
from fastapi.responses import JSONResponse
from typing import List
from contextlib import asynccontextmanager
from databases import Database
from .db import initialize_tables,DB
from .schema import CreateItems,CreateStores,Receipt
from src.utils import generate_unique_string
import pymysql



@asynccontextmanager
async def lifespan(_app: FastAPI):
    await DB.connect()
    await initialize_tables(DB)
    yield
    await DB.disconnect()

    

app=FastAPI(lifespan=lifespan)

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

async def create_receipt_items(items):
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
            await DB.execute("INSERT INTO ReceiptItems (name,item_code,item_name,bill_item_name,price,mrp,idx,receipt_id) VALUES (:name,:item_code,:item_name,:bill_item_name,:price,:mrp,:idx,:receipt_id)", values=items)
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
                id = await DB.execute("INSERT INTO Receipt (posting_date,posting_time,store_receipt_no,receipt_store_name,total_amount,store_id,store_name) VALUES (:posting_date,:posting_time,:store_receipt_no,:receipt_store_name,:total_amount,:store_id,:store_name)", values=rec)
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
    return JSONResponse(content="Sucessfull", status_code=201)
    

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
    
    
