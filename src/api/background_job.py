import copy
import json

from src.api.process_receipt import process_emf,process_esc_p
from src.api.file_type import add_file_tag_to_db,get_file_tag
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

    items_dict={
        'observed_name': None,
        'guessed_full_name': None,
        'qty': None,
        'uom': None,
        'mrp': None,
        'price': None,
        'total_amount': None,
        'barcode': None
    }

    if 'items' in data:
        for item in data['items']:
            if type(item)!=dict:
                continue
            db_copy=copy.copy(db_fields)
            db_copy['processed_receipt_id']=id

            for key in items_dict:
                try:
                    db_copy[key] = item[key]
                except Exception as e:
                    pass
            parsed_items.append(db_copy)
    return parsed_items

async def type_correction(data):
    db_fields = {
        'creation' : str,
        'observed_name': str,
        'guessed_full_name': str,
        'qty': float,
        'uom': str,
        'mrp': float,
        'price': float,
        'total_amount': float,
        'barcode': str,
        'date': str,
        'time': str,
        'store_name': str,
        'store_address': str,
        'bill_id': str,
        'gstin': str,
        'total_qty': float,
        'total_items': float,
        'final_amount': float,
        'store_cashier': str,
        'store_phone_no': str,
        'store_email': str,
        'customer_phone_number': str,
        'mode_of_payment': str,
        'customer_name': str,
        'customer_details': str
        }
    for i in data:
        for key in i:
            if i[key] is None:
                continue  # Skip None values
            if key in db_fields and type(i[key]) != db_fields[key]:
                try:
                    i[key] = db_fields[key](i[key])
                except (ValueError, TypeError):
                    i[key] = None
                    # If conversion fails, set to None
    return data

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
    
    file_type,file_sub_type = await get_file_tag(file_content)
    await add_file_tag_to_db(id,file_type,file_sub_type)

    if file_type=='EMF':
        prc_rec_id,processed_text=await process_emf.process_receipt(id,file_content)

    elif file_type=='ESC/P':
        prc_rec_id,processed_text=await process_esc_p.process_receipt(id,file_content)

    if prc_rec_id and processed_text:
        processed_json = invoke_model(processed_text)
        await update_json_to_table(prc_rec_id,processed_json)
        parsed_items = await parse_receipt(prc_rec_id,json.loads(processed_json))
        parsed_items = await type_correction(parsed_items)
        if parsed_items:
            await insert_parsed_items(parsed_items)