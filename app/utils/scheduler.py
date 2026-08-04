from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pytz
from flask import current_app

IST = pytz.timezone('Asia/Kolkata')
scheduler = BackgroundScheduler(timezone=IST)

def check_pending_settlements(app):
    with app.app_context():
        from app import get_db
        from app.utils.email_service import send_reminder_email
        db = get_db()
        
        now = datetime.now(IST)
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        splits = list(db.splits.find({'status': 'active', 'createdAt': {'$lt': twenty_four_hours_ago}}))
        
        for split in splits:
            for settlement in split.get('settlements', []):
                if settlement['status'] == 'pending':
                    # Check if reminder was sent in last 24h
                    recent_log = db.email_logs.find_one({
                        'splitId': split['_id'],
                        'debtorName': db.users.find_one({'_id': settlement['fromUserId']}).get('displayName'),
                        'timestamp': {'$gt': twenty_four_hours_ago},
                        'status': 'success'
                    })
                    
                    if not recent_log:
                        debtor = db.users.find_one({'_id': settlement['fromUserId']})
                        creditor = db.users.find_one({'_id': settlement['toUserId']})
                        
                        if debtor and creditor and debtor.get('email'):
                            send_reminder_email(
                                to_email=debtor['email'],
                                debtor_name=debtor.get('displayName', debtor['username']),
                                creditor_name=creditor.get('displayName', creditor['username']),
                                amount=settlement['amount'],
                                split_description=split.get('description', 'Untitled Split'),
                                split_date=split.get('createdAt').strftime('%Y-%m-%d %H:%M:%S'),
                                split_id=split['_id'],
                                db=db
                            )

def init_scheduler(app):
    if not scheduler.running:
        scheduler.add_job(func=check_pending_settlements, trigger="interval", hours=1, args=[app], id='email_reminders', replace_existing=True)
        scheduler.start()
