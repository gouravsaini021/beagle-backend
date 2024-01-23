from typing import Optional,List
from pydantic import BaseModel
from datetime import date, time

class Item(BaseModel):
    item_code: str
    item_name: str
    category:Optional[str] = None
    brand:Optional[str] = None
    barcode:Optional[str] = None
    mrp: Optional[float] = None

class CreateItems(BaseModel):
    items:List[Item]

class Store(BaseModel):
    store_id:str
    store_name:str
    address:Optional[str] = None
    city:Optional[str] = None
    state:Optional[str] = None
    pincode:Optional[str] = None
    country:Optional[str] = None
    latitude:Optional[float] = None
    longitude:Optional[float] = None

class CreateStores(BaseModel):
    stores:List[Store]
    

class ReceiptItems(BaseModel):
    bill_item_name:str
    qty: Optional[int]
    item_code:Optional[str] = None
    item_name:Optional[str] = None
    price:float
    mrp:Optional[float]=None

class Receipt(BaseModel):
    posting_date:date
    posting_time:time
    store_receipt_no:Optional[str] = None
    receipt_store_name:Optional[str] = None
    total_amount:Optional[float] = None
    store_id:Optional[str] = None
    receipt_items:List[ReceiptItems]






