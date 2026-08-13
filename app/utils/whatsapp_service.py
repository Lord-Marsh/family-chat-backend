import requests
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

# Using the provided credentials
WHATSAPP_PHONE_NUMBER_ID = "1275108672350151"
WHATSAPP_ACCESS_TOKEN = "EAAV7n6OJoowBSAACZBp4XW3XZCGsgeaAGmqR761v5vCPsAf9wtiG1LfpZAyqZC0q1I89UY9DBpex9DOwiw5FpS3oKjZC9iJESP9hW2T68ZBNxE78ktDnGYPlQT8iRarkmZCpj9lzCmxsZAAZCZBaZAyj5km7r6tvB6y54zcnp1ZBnvHY1x6XwhuuCP5MKVayeB4SZBT10e5l6rj6PmFuK16SR3SkgZBdcCG7xV9wj6WJSb"
TEMPLATE_NAME = "settlement_reminder"

def send_whatsapp_reminder(phone_number, debtor_name, amount,
                           creditor_name, split_description,
                           split_date, split_id, db):
    """Send a WhatsApp template message for pending settlement."""
    
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": debtor_name},
                        {"type": "text", "text": str(round(amount))},
                        {"type": "text", "text": creditor_name},
                        {"type": "text", "text": split_description},
                        {"type": "text", "text": split_date}
                    ]
                }
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        # Log the attempt
        db.whatsapp_logs.insert_one({
            'splitId': split_id,
            'phone': phone_number,
            'debtorName': debtor_name,
            'status': 'success' if response.status_code == 200 else 'failed',
            'statusCode': response.status_code,
            'response': response.json() if response.text else {},
            'timestamp': datetime.now(IST)
        })
        
        return response.status_code == 200
    except Exception as e:
        print(f"WhatsApp Request Failed: {e}")
        db.whatsapp_logs.insert_one({
            'splitId': split_id,
            'phone': phone_number,
            'debtorName': debtor_name,
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now(IST)
        })
        return False
