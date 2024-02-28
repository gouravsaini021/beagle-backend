import boto3
from requests_toolbelt.multipart import decoder
import re




def upload_to_s3(content,filename):
    from src import AWS_ACCESS_KEY_ID,AWS_SECRET_ACCESS_KEY
    s3 = boto3.resource('s3',aws_access_key_id=AWS_ACCESS_KEY_ID,aws_secret_access_key=AWS_SECRET_ACCESS_KEY)
    s3.Object('beaglebucket',filename).put(Body=content)

def clean_file(body,header):
    endswith=".bin"
    boundary = body[:body.find(b'\r\n')]
    while boundary[0] == "-":
        boundary = boundary[1:]
    de=decoder.MultipartDecoder(content=body,content_type=header).parts
    content=de[0].content
    headers=de[0].headers[b'Content-Disposition'].decode("utf-8")
    filename_match = re.search(r'filename[^;=\n]*=["\']?([^"\';\n]+)',headers )
    if filename_match:
        filename = filename_match.group(1)
        if filename.endswith(".SPL"):
                endswith=".SPL"
        elif filename.endswith(".SHD"):
                endswith=".SHD"
    return endswith,content
    
    