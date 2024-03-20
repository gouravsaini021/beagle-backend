import copy

from src.api.process_receipt import process_receipt
from src.api.claude import invoke_model
from src.db import DB
from src.utils import ist_datetime_current,generate_unique_string

async def parse_receipt(id,data):
    parsed_items=[]
    db_fields = {
        'creation': ist_datetime_current(),
        'observed_name': None,
        'guessed_full_name': None,
        'qty': None,
        'uom': None,
        'mrp': None,
        'price': None,
        'total_amount': None,
        'barcode': None,
        'date': None,
        'time': None,
        'store_name': None,
        'store_address': None,
        'bill_id': None,
        'gstin': None,
        'total_qty': None,
        'total_items': None,
        'final_amount': None,
        'store_cashier': None,
        'store_phone_no': None,
        'store_email': None,
        'customer_phone_number': None,
        'mode_of_payment': None,
        'customer_name': None,
        'customer_details': None
        }
    for key in db_fields:
        try:
            db_fields[key] = data[key]
        except Exception as e:
            pass
    
    for item in data['items']:
        db_copy=copy.copy(db_fields)
        db_copy['processed_receipt_id']=id
        for key in item:
            try:
                db_copy[key] = item[key]
            except Exception as e:
                pass
        parsed_items.append(db_copy)
    return parsed_items

async def insert_parsed_items(parsed_items):
    insert_query = """INSERT INTO ParsedItem 
                                (creation, processed_receipt_id, observed_name, guessed_full_name, qty, uom, 
                                mrp, price, total_amount, barcode, date, time, store_name, store_address, 
                                bill_id, gstin, total_qty, total_items, final_amount, store_cashier, 
                                store_phone_no, store_email, customer_phone_number, mode_of_payment, 
                                customer_name, customer_details) 
                                VALUES 
                                (:creation, :processed_receipt_id, :observed_name, :guessed_full_name, :qty, :uom, 
                                :mrp, :price, :total_amount, :barcode, :date, :time, :store_name, :store_address, 
                                :bill_id, :gstin, :total_qty, :total_items, :final_amount, :store_cashier, 
                                :store_phone_no, :store_email, :customer_phone_number, :mode_of_payment, 
                                :customer_name, :customer_details)"""

    async with DB.transaction():
        await DB.execute_many(insert_query, parsed_items)


async def update_json_to_table(id,processed_json):
    current_time=ist_datetime_current()
    async with DB.transaction():
        values={'processed_json':processed_json,"id":id,"modified":current_time}
        id=await DB.execute("""UPDATE ProcessedReceipt SET processed_json = :processed_json, modified = :modified WHERE id = :id""", values=values)


async def background_task_for_softupload(id:int,file_content:bytes):
    prc_rec_id,processed_text=await process_receipt(id,file_content)
    if prc_rec_id and processed_text:
        processed_json=invoke_model(processed_text)
        await update_json_to_table(prc_rec_id,processed_json)
        parsed_items=await parse_receipt(prc_rec_id,processed_json)
        if parsed_items:
            await insert_parsed_items(parsed_items)