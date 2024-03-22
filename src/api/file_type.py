import struct
import magic
from typing import Union,Tuple,Optional

from src.db import DB
from src.utils import ist_datetime_current,generate_unique_string


class EMF:
    def __init__(self,hex:bytes):
        self.emf_subtype=set()
        self.is_emf=False
        try:
            signature,emr_record=self.get_header_signature_and_emr_record(hex)
            if self.check_emf(signature):
                self.process_emr_records(emr_record)
        except Exception as e:
            pass


    def check_emf(self,signature):
        if signature == (b' ', b'E', b'M', b'F'):
            self.is_emf=True
            return True
        return False
        

    def get_header_signature_and_emr_record(self,hex):
        header_size=struct.unpack_from("i",hex,4)[0]
        page_content_size=struct.unpack_from("i",hex,header_size+4)[0]
        page_content=hex[header_size:header_size+page_content_size]
        page_content_header_size=struct.unpack_from("i",page_content,12)[0]
        signature=struct.unpack_from("4c",page_content,48)
        return signature,page_content[page_content_header_size+8:]
        
    def process_emr_records(self,emf:bytes):

        length=len(emf)
        while length>0:
            emf_type,size=struct.unpack("2I",emf[:8])
            if emf_type==83:
                self.emf_subtype.add("EXTTEXTOUTA")
            elif emf_type==84:
                self.emf_subtype.add("EXTTEXTOUTW")
            elif emf_type==85:
                self.emf_subtype.add("POLYBEZIER16")
            elif emf_type==88:
                self.emf_subtype.add('POLYBEZIERTO16')

            emf=emf[size:]
            length-=size

def is_pdf(file_content:bytes):
    file_type = magic.from_buffer(file_content, mime=True)
    if file_type=="application/pdf":
        print(file_type)
        return True
    return False

def is_TSPL_EZD(file_content:bytes):
    substrings_to_check = [b'TEXT', b'GAP', b'SIZE',b'PRINT',b'CLS']
    for substring in substrings_to_check:
        if file_content.startswith(substring):
            return True
    return False

async def get_file_tag(file_content:bytes) -> Tuple[str, Optional[str]]:
    file_type: str
    file_subtype: Optional[str] = None
    emf=EMF(file_content)
    if emf.is_emf:
        file_type="EMF"
        if emf.emf_subtype:
            file_subtype=str(list(emf.emf_subtype))

    elif file_content[:4]==b'\x1b\x4d\x1b\x4d':
        file_type='ESC/P'
    elif file_content[20:22]==b'\x1b\x63' :
        file_type="ESC/TVS"
    elif is_pdf(file_content):
        file_type="PDF"
    elif file_content[:4]==b'\x50\x4b\x03\x04':
        file_type='XPS'
    elif is_TSPL_EZD(file_content):
        file_type='TSPL-EZ'
    
    return file_type,file_subtype

async def add_file_tag_to_db(id:int,file_type:str,file_sub_type):
    if file_type:
        values={"creation":ist_datetime_current(), "softupload_id":id, "type":file_type, "sub_type":file_sub_type}
        insert_query = """INSERT INTO TagSoftUpload 
                                (creation, softupload_id, type, sub_type) 
                                VALUES 
                                (:creation, :softupload_id, :type, :sub_type)"""

        async with DB.transaction():
            await DB.execute(insert_query,values)
