import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app
from datetime import datetime
import pytz
from app.utils.id_generator import generate_email_log_id

IST = pytz.timezone('Asia/Kolkata')

def send_reminder_email(to_email, debtor_name, creditor_name, amount, split_description, split_date, split_id, db):
    host = current_app.config['SMTP_HOST']
    port = current_app.config['SMTP_PORT']
    sender_email = current_app.config['SMTP_EMAIL']
    password = current_app.config['SMTP_PASSWORD']
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"SplitPay Reminder: You owe {creditor_name} ₹{amount}"
    msg['From'] = sender_email
    msg['To'] = to_email
    
    html = f"""
    <html>
      <body>
        <h2>SplitPay Reminder</h2>
        <p>Hi {debtor_name},</p>
        <p>This is a reminder that you owe <strong>{creditor_name}</strong> an amount of <strong>₹{amount}</strong> for the split <strong>"{split_description}"</strong> created on {split_date}.</p>
        <p>Please clear this pending settlement soon.</p>
        <br/>
        <p>Thanks,<br/>SplitPay Team</p>
      </body>
    </html>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    success = False
    error_msg = ""
    
    try:
        server = smtplib.SMTP(host, port)
        server.starttls()
        server.login(sender_email, password)
        server.send_message(msg)
        server.quit()
        success = True
    except Exception as e:
        error_msg = str(e)
        success = False
        
    # Log the email
    log_doc = {
        '_id': generate_email_log_id(),
        'toEmail': to_email,
        'debtorName': debtor_name,
        'creditorName': creditor_name,
        'amount': amount,
        'splitId': split_id,
        'timestamp': datetime.now(IST),
        'status': 'success' if success else 'failed',
        'error': error_msg if not success else None
    }
    
    try:
        db.email_logs.insert_one(log_doc)
    except:
        pass
        
    return success
