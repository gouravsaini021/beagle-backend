import struct
from PIL import Image, ImageDraw, ImageFont
import io
from typing import Optional, Tuple , Union

from src.db import DB
from src.s3 import upload_to_s3
from src.utils import ist_datetime_current




class Bounds:
      def __init__(self,bounds):
            self.left=bounds[0] if bounds[0] != 4294967295 else 0
            self.top=bounds[1]  if bounds[1] != 4294967295 else 0
            self.right=bounds[2] if bounds[2] != 4294967295 else 0
            self.bottom=bounds[3] if bounds[3] != 4294967295 else 0

class Fonts:
    def __init__(self,size,bold,italic,underline):
         self.type="Font"
         self.size=size
         self.bold=bold
         self.italic=italic
         self.underline=underline


class EMF_DATA:
      def __init__(self,text:str,bounds:Bounds,size:int):
            self.type="Text"
            self.text=text
            self.bounds=bounds
            self.size=size

class EMF:
    def __init__(self,hex):
        self.hex=hex
        self.text=""
        self.emf_data=[]
        self.emf_subtype=set()
        self.is_emf=False
        signature,emr_record=self.get_header_signature_and_emr_record(hex)
        if self.check_emf(signature):
            self.process_emr_records(emr_record)

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
            type,size=struct.unpack("2I",emf[:8])
            if type==84:
                self.EMRExtTextOutW(emf[:size])
            if type==82:
                 self.EMR_EXTCREATEFONTINDIRECTW(emf[:size])
            if type==88:
                pass
            emf=emf[size:]
            length-=size
    
    def EMR_EXTCREATEFONTINDIRECTW(self,emf):
        font_size=struct.unpack_from("i",emf,12)[0]
        weight,italic,underline=struct.unpack_from("I??",emf,28)
        face_name=struct.unpack_from("68c",emf,60)
        self.emf_data.append(Fonts(size=abs(font_size),bold=weight,italic=italic,underline=underline))
         

    def EMRExtTextOutW(self,emf):
        char_size=struct.unpack_from("I",emf,44)[0]
        bounds=Bounds(struct.unpack_from("4I",emf,8))
        text_starting_bytes=emf[76:]
        text=""
        for i in range(char_size):
            bytes=text_starting_bytes[2*i:2*i+2]
            text+=bytes.decode('utf-16le')
        self.text+=text
        self.emf_data.append(EMF_DATA(text,bounds,char_size))




def draw_emf_data_to_image(emf_data_list):
    """
    Draws the text from EMF data onto an image, with the image size dynamically calculated
    from the bounding boxes of the EMF data.
    
    :param emf_data_list: List of EMF_Data objects containing text and bounding boxes.
    """
    # First, find the max width and height required for the image
    max_width, max_height = 0, 0
    for data in emf_data_list:
        if data.type=='Text':
            if data.bounds is None:
                continue
            if data.text == "":
                continue
            x1, y1, x2, y2 = data.bounds.left, data.bounds.top, data.bounds.right, data.bounds.bottom
            max_width = max(max_width, x2)
            max_height = max(max_height, y2)

    # Add a margin if necessary
    margin = 10
    image_size = (max_width + margin, max_height + margin)
    
    image = Image.new('RGB', image_size, 'white')
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("times new roman.ttf", 12)
    except IOError:
        font = ImageFont.load_default()
        

    # Loop through each EMF_Data and draw the ASCII text
    for data in emf_data_list:
        if data.type=="Text":
            x1, y1, x2, y2 = data.bounds.left, data.bounds.top, data.bounds.right, data.bounds.bottom
            draw.text((x1, y1), data.text, fill="black", font=font)
        elif data.type=="Font":
            if data.size>0:
                try:
                    font = ImageFont.truetype("times new roman.ttf", data.size)
                except IOError:
                    font = ImageFont.load_default()


    # Save the image to the bytes buffer
    byte_io = io.BytesIO()
    image.save(byte_io, 'JPEG')
    byte_io.seek(0)
    binary_data = byte_io.getvalue()
    return binary_data


def emf_data_to_string(emf_data_list):
    t=[]
    for data in emf_data_list:
            if data.type=="Text":
                if data.bounds is None:
                    continue
                if data.text == "":
                    continue
                left,top,right,bottom = data.bounds.left, data.bounds.top, data.bounds.right, data.bounds.bottom
                t.append((data.text,left,top))
    t.sort(key=lambda x: (x[2],x[1]))
    final_string=""
    cur_y=0
    for i in t:
        if cur_y !=i[2]:
              cur_y=i[2]
              final_string+="\n"
        final_string+=i[0]+" "
    
    return final_string



async def process_receipt(id:int,file_content:bytes) -> Union[Tuple[int, str], Tuple[bool, bool]]:

    if file_content :
           
        try:
            emf=EMF(file_content)
            emf_data=emf.emf_data
        except Exception as e:
            return (False,False)
        
        if emf_data and emf.is_emf:
            binary_image_data=draw_emf_data_to_image(emf_data)
            text_from_image=emf_data_to_string(emf_data)
            current_time=ist_datetime_current()
            filename=f"{id}.jpeg"
            image_path="processed_images/"+filename
            image_link='https://beaglebucket.s3.amazonaws.com/'+image_path
            upload_to_s3(binary_image_data,image_path)

            iv={"creation":current_time,"modified":current_time,"soft_upload_id":id,"image_link":image_link,"image_path":image_path,'is_processed':1,"processed_text":text_from_image}

            async with DB.transaction():
                    id=await DB.execute("INSERT INTO ProcessedReceipt (creation,modified,soft_upload_id,image_link,image_path,is_processed,processed_text) VALUES (:creation,:modified,:soft_upload_id,:image_link,:image_path,:is_processed,:processed_text)", values=iv)
            
            return (id,text_from_image)
    return (False,False)