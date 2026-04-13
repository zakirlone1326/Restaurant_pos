import requests

def send_staff_notification(phone_number, message):
    # 1. First, always print to console so you can debug without spending money
    print(f"\n📢 [LOGGING SMS]: To {phone_number} -> {message}\n")

    # 2. Real SMS Integration (Example: Fast2SMS)
    # Get a free API key from fast2sms.com
    url = "https://www.fast2sms.com/dev/bulkV2"
    
    api_key = "YOUR_FREE_API_KEY_HERE" # Put your real key here
    
    payload = {
        "message": message,
        "language": "english",
        "route": "q", # 'q' is for Quick SMS
        "numbers": phone_number,
    }
    
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json"
    }

    try:
        # This actually sends the web request to the SMS provider
        response = requests.get(url, params=payload, headers=headers)
        print(f"SMS Provider Response: {response.json()}")
    except Exception as e:
        print(f"Failed to connect to SMS API: {e}")