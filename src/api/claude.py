import base64
import json
import logging
import backoff
import boto3
from botocore.exceptions import ClientError
import json
import concurrent.futures
from tqdm import tqdm
logger = logging.getLogger(__name__)
import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

config=Config(connect_timeout=5, read_timeout=60, retries={'max_attempts': 10})


prompt = ""
system_prompt='''
You are a helpful assistant designed to output JSON. You read bills and do not make up items. You will give me fields as observed_name, guessed_full_name (Predict the guessed_full_name from the observed_name and return the full name. 
DO NOT MAKE UP NAMES YOURSELF.), qty, mrp, price, total_amount, barcode, amount, date (yyyy-mm-dd), time (HH:MM:SS), store_name, address, gstin, total_qty, total_items, final_amount, bill or receipt id, gstin, store_cashier, store_phone_no, store_email, customer_phone_number, mode_of_payment, customer_name, customer_details. 
Feel free to leave the field empty if you can't find a field, and if you find extra fields please add to JSON. I am also adding the json format expected below and if you don't find items can return empty json.
Start your response with only valid json, do not output anytext in front of it. please. directly start from {"store_name":. Here is the example:
                {
                "store_name": "Best Buy Mart",
                "store_address": "No. 15, MG Road, Opp. Metro Station, New Delhi - 110001",
                "gstin": "07AABCT3518Q1ZV",
                "bill_id": "45682",
                "store_cashier": "Rajesh",
                "store_phone_no": "9876543210",
                "store_email": "bestbuymart@gmail.com",
                "customer_name": "Rahul",
                "customer_details": "Card Number XXX3883",
                "mode_of_payment": "Visa",
                "date": "2024-03-15",
                "time": "15:30:00",
                "total_qty": 4,
                "total_items": 3,
                "final_amount": 350.00,
                "items": [
                    {
                    "observed_name": "BRTNA BRED",
                    "guessed_full_name": "Britannia Bread",
                    "qty": 2,
                    "mrp": 30.00,
                    "price": 28.00,
                    "total_amount": 56.00,
                    "barcode": null
                    },
                    {
                    "observed_name": "TAAZA1L",
                    "guessed_full_name": "Amul Taaza Milk 1L",
                    "qty": 2,
                    "mrp": 48.00,
                    "price": 42.00,
                    "total_amount": 84.00,
                    "barcode": null
                    }
                ]
                }

'''

"""
Invokes Anthropic Claude 3 Haiku to run an inference using the input
provided in the request body.

:param prompt: The prompt that you want Claude 3 to complete.
:return: Inference response from the model.
"""

# Initialize the Amazon Bedrock runtime client
client = boto3.client(
    service_name="bedrock-runtime", region_name="us-east-1"
)

# Invoke Claude 3 with the text prompt
#model_id = "anthropic.claude-3-haiku-20240307-v1:0"
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
def need_to_retry(e):
    return "ThrottlingException" in str(e) or "ModelTimeoutException" in str(e)

@backoff.on_exception(backoff.expo, Exception, max_tries=5, giveup=need_to_retry)
def invoke_model(prompt):
    try:
        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 2048,
                    "system": system_prompt,
                    "messages": [
                        
                        {
                            "role": "user",
                            "content": [{"type": "text", "text": prompt}],
                        }
                    ],
                }
            ),
        )

        # Process and print the response
        result = json.loads(response.get("body").read())
        input_tokens = result["usage"]["input_tokens"]
        output_tokens = result["usage"]["output_tokens"]
        output_list = result.get("content", [])

        # print("Invocation details:")
        # print(f"- The input length is {input_tokens} tokens.")
        # print(f"- The output length is {output_tokens} tokens.")
        response = ''
        # print(f"- The model returned {len(output_list)} response(s):")
        for output in output_list:
            response += (output["text"])

        return response

    except ClientError as err:
        logger.error(
            "Couldn't sonnet Claude 3 Haiku. Here's why: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
