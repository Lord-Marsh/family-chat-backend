import random
import string
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def _generate_suffix():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def _get_timestamp():
    return datetime.now(IST).strftime('%Y%m%d-%H%M%S')

def generate_split_id():
    return f"SPL-{_get_timestamp()}-{_generate_suffix()}"

def generate_login_log_id():
    return f"LOG-LGN-{_get_timestamp()}-{_generate_suffix()}"

def generate_email_log_id():
    return f"LOG-EML-{_get_timestamp()}-{_generate_suffix()}"

def generate_activity_log_id():
    return f"LOG-ACT-{_get_timestamp()}-{_generate_suffix()}"
