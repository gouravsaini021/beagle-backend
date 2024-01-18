import uuid
def generate_unique_string(length:int=8) -> str:
    unique_string = str(uuid.uuid4()).replace("-","")
    return unique_string[:length]