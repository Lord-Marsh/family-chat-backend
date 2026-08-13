from flask import Blueprint, request, jsonify
from app import get_db, socketio
from app.utils.auth import token_required, sa_required
from app.utils.id_generator import generate_split_id, generate_activity_log_id
from app.utils.settlement import calculate_settlements
from datetime import datetime
import pytz
from math import ceil

split_bp = Blueprint('splits', __name__)
IST = pytz.timezone('Asia/Kolkata')

def log_activity(db, action, user_id, details=None):
    log = {
        '_id': generate_activity_log_id(),
        'userId': user_id,
        'action': action,
        'details': details or {},
        'timestamp': datetime.now(IST)
    }
    db.activity_logs.insert_one(log)

def serialize_doc(doc):
    if isinstance(doc, dict):
        return {k: serialize_doc(v) for k, v in doc.items()}
    elif isinstance(doc, list):
        return [serialize_doc(i) for i in doc]
    elif isinstance(doc, datetime):
        return doc.isoformat()
    return doc

@split_bp.route('', methods=['POST'])
@token_required
def create_split(current_user_id):
    db = get_db()
    data = request.get_json()
    
    total_amount = float(data.get('totalAmount', 0))
    split_among = data.get('splitAmong', [])
    
    if data.get('splitType') == 'equal':
        share = round(total_amount / len(split_among)) if split_among else 0
        for p in split_among:
            p['share'] = share
            
    settlements = calculate_settlements(data.get('paidBy', []), split_among)
    
    split_id = generate_split_id()
    
    split_doc = {
        '_id': split_id,
        'description': data.get('description'),
        'totalAmount': total_amount,
        'category': data.get('category'),
        'paidBy': data.get('paidBy', []),
        'splitAmong': split_among,
        'splitType': data.get('splitType', 'custom'),
        'settlements': settlements,
        'status': 'active' if settlements else 'settled',
        'createdBy': current_user_id,
        'createdAt': datetime.now(IST)
    }
    
    db.splits.insert_one(split_doc)
    
    log_activity(db, 'create_split', current_user_id, {'splitId': split_id})
    socketio.emit('split_created', serialize_doc(split_doc), to='splitpay_room')
    
    return jsonify(split_doc), 201

@split_bp.route('', methods=['GET'])
@token_required
def get_splits(current_user_id):
    db = get_db()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 10))
    status = request.args.get('status')
    category = request.args.get('category')
    member = request.args.get('member')
    
    query = {}
    if status and status != 'all':
        query['status'] = status
    if category:
        query['category'] = category
    if member:
        query['$or'] = [{'paidBy.userId': member}, {'splitAmong.userId': member}]
        
    skip = (page - 1) * limit
    cursor = db.splits.find(query).sort('createdAt', -1).skip(skip).limit(limit)
    splits = list(cursor)
    total = db.splits.count_documents(query)
    
    # Resolve usernames for UI
    users = {u['_id']: u.get('displayName', u['username']) for u in db.users.find()}
    
    for split in splits:
        for p in split.get('paidBy', []):
            p['displayName'] = users.get(p['userId'], 'Unknown')
        for s in split.get('splitAmong', []):
            s['displayName'] = users.get(s['userId'], 'Unknown')
        for stl in split.get('settlements', []):
            stl['fromDisplayName'] = users.get(stl['fromUserId'], 'Unknown')
            stl['toDisplayName'] = users.get(stl['toUserId'], 'Unknown')
            
    return jsonify({
        'splits': splits,
        'total': total,
        'page': page,
        'limit': limit,
        'totalPages': ceil(total / limit) if limit > 0 else 0
    }), 200

@split_bp.route('/<split_id>', methods=['GET'])
@token_required
def get_split(current_user_id, split_id):
    db = get_db()
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return jsonify({'message': 'Split not found'}), 404
        
    users_full = {u['_id']: u for u in db.users.find()}
    users = {u['_id']: u.get('displayName', u['username']) for u in db.users.find()}
    
    for p in split.get('paidBy', []):
        p['displayName'] = users.get(p['userId'], 'Unknown')
    for s in split.get('splitAmong', []):
        s['displayName'] = users.get(s['userId'], 'Unknown')
    for stl in split.get('settlements', []):
        stl['fromDisplayName'] = users.get(stl['fromUserId'], 'Unknown')
        stl['toDisplayName'] = users.get(stl['toUserId'], 'Unknown')
        stl['toUserUpiId'] = users_full.get(stl['toUserId'], {}).get('upiId')
        
    return jsonify(split), 200

@split_bp.route('/<split_id>', methods=['PUT'])
@token_required
def update_split(current_user_id, split_id):
    db = get_db()
    data = request.get_json()
    
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return jsonify({'message': 'Split not found'}), 404
        
    user = db.users.find_one({'_id': current_user_id})
    is_sa = user and user.get('userType') == 'sa'
    
    if not is_sa and split.get('createdBy') != current_user_id:
        return jsonify({'message': 'Unauthorized to update this split'}), 403
        
    total_amount = float(data.get('totalAmount', split['totalAmount']))
    split_among = data.get('splitAmong', split['splitAmong'])
    paid_by = data.get('paidBy', split['paidBy'])
    
    if data.get('splitType') == 'equal':
        share = round(total_amount / len(split_among)) if split_among else 0
        for p in split_among:
            p['share'] = share
            
    settlements = calculate_settlements(paid_by, split_among)
    
    # Merge existing settlements statuses if possible based on from/to users
    # For simplicity, if amounts changed significantly, they may reset to pending
    
    updates = {
        'description': data.get('description', split['description']),
        'totalAmount': total_amount,
        'category': data.get('category', split['category']),
        'paidBy': paid_by,
        'splitAmong': split_among,
        'splitType': data.get('splitType', split.get('splitType')),
        'settlements': settlements,
        'status': 'active' if settlements else 'settled',
        'updatedAt': datetime.now(IST)
    }
    
    db.splits.update_one({'_id': split_id}, {'$set': updates})
    
    updated_split = db.splits.find_one({'_id': split_id})
    log_activity(db, 'update_split', current_user_id, {'splitId': split_id})
    socketio.emit('split_updated', serialize_doc(updated_split), to='splitpay_room')
    
    return jsonify(updated_split), 200

@split_bp.route('/<split_id>', methods=['DELETE'])
@token_required
def delete_split(current_user_id, split_id):
    db = get_db()
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return jsonify({'message': 'Split not found'}), 404
        
    user = db.users.find_one({'_id': current_user_id})
    is_sa = user and user.get('userType') == 'sa'
    
    if not is_sa and split.get('createdBy') != current_user_id:
        return jsonify({'message': 'Unauthorized to delete this split'}), 403
        
    db.splits.delete_one({'_id': split_id})
    
    log_activity(db, 'delete_split', current_user_id, {'splitId': split_id})
    socketio.emit('split_deleted', {'splitId': split_id}, to='splitpay_room')
    
    return jsonify({'message': 'Split deleted'}), 200

@split_bp.route('/<split_id>/settle', methods=['POST'])
@token_required
def settle_payment(current_user_id, split_id):
    db = get_db()
    data = request.get_json()
    settlement_id = data.get('settlementId')
    
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return jsonify({'message': 'Split not found'}), 404
        
    settlements = split.get('settlements', [])
    updated = False
    all_paid = True
    
    for stl in settlements:
        if stl['id'] == settlement_id:
            if current_user_id not in [stl['fromUserId'], stl['toUserId']]:
                return jsonify({'message': 'Unauthorized to settle this'}), 403
                
            stl['status'] = 'paid'
            stl['paidAt'] = datetime.now(IST)
            stl['note'] = data.get('note', '')
            stl['markedBy'] = current_user_id
            stl['markedAt'] = datetime.now(IST)
            updated = True
            
        if stl['status'] != 'paid':
            all_paid = False
            
    if not updated:
        return jsonify({'message': 'Settlement not found'}), 404
        
    updates = {'settlements': settlements}
    if all_paid:
        updates['status'] = 'settled'
        
    db.splits.update_one({'_id': split_id}, {'$set': updates})
    
    updated_split = db.splits.find_one({'_id': split_id})
    log_activity(db, 'settle_payment', current_user_id, {'splitId': split_id, 'settlementId': settlement_id})
    socketio.emit('settlement_updated', serialize_doc(updated_split), to='splitpay_room')
    
    return jsonify(updated_split), 200

@split_bp.route('/<split_id>/settle/<settlement_id>', methods=['PUT'])
@token_required
def revert_settlement(current_user_id, split_id, settlement_id):
    db = get_db()
    data = request.get_json() or {}
    
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return jsonify({'message': 'Split not found'}), 404
        
    settlements = split.get('settlements', [])
    updated = False
    
    user = db.users.find_one({'_id': current_user_id})
    is_sa = user and user.get('userType') == 'sa'

    for stl in settlements:
        if stl['id'] == settlement_id:
            # Check authorization: SA can revert anytime. 
            # Normal user can only revert if they marked it AND it was < 10 mins ago.
            if not is_sa:
                if stl['markedBy'] != current_user_id:
                    return jsonify({'message': 'Unauthorized to revert this settlement'}), 403
                if stl.get('paidAt'):
                    time_diff = (datetime.utcnow() - stl['paidAt']).total_seconds() / 60
                    if time_diff > 10:
                        return jsonify({'message': 'Can only revert within 10 minutes of marking as paid'}), 403
                        
            if 'note' in data:
                stl['note'] = data['note']
            else:
                stl['status'] = 'pending'
                stl['paidAt'] = None
                stl['note'] = ''
                stl['markedBy'] = None
                stl['markedAt'] = None
            updated = True
            break
            
    if not updated:
        return jsonify({'message': 'Settlement not found'}), 404
        
    updates = {'settlements': settlements}
    # Check if we need to revert split status
    if split['status'] == 'settled' and not all(s['status'] == 'paid' for s in settlements):
        updates['status'] = 'active'
        
    db.splits.update_one({'_id': split_id}, {'$set': updates})
    
    updated_split = db.splits.find_one({'_id': split_id})
    log_activity(db, 'revert_settlement', current_user_id, {'splitId': split_id, 'settlementId': settlement_id})
    socketio.emit('split_updated', {'splitId': split_id})
    return jsonify({'message': 'Settlement reverted successfully'})

@split_bp.route('/remind-all-whatsapp', methods=['POST'])
@token_required
@sa_required
def remind_all_whatsapp(current_user_id):
    from app import get_db
    from app.utils.whatsapp_service import send_whatsapp_reminder
    db = get_db()
    
    # Get all active splits
    splits = list(db.splits.find({'status': 'active'}))
    messages_sent = 0
    failed_messages = 0
    
    for split in splits:
        for settlement in split.get('settlements', []):
            if settlement['status'] == 'pending':
                debtor = db.users.find_one({'_id': settlement['fromUserId']})
                creditor = db.users.find_one({'_id': settlement['toUserId']})
                
                if debtor and creditor and debtor.get('phone'):
                    success = send_whatsapp_reminder(
                        phone_number=debtor['phone'],
                        debtor_name=debtor.get('displayName', debtor['username']),
                        amount=settlement['amount'],
                        creditor_name=creditor.get('displayName', creditor['username']),
                        split_description=split.get('description', 'Untitled Split'),
                        split_date=split.get('createdAt').strftime('%d %b %Y'),
                        split_id=split['_id'],
                        db=db
                    )
                    if success:
                        messages_sent += 1
                    else:
                        failed_messages += 1
                        
    log_activity(db, 'admin_wa_remind_all', current_user_id, {'sent': messages_sent, 'failed': failed_messages})
    return jsonify({
        'message': f'Reminder blast complete. {messages_sent} sent, {failed_messages} failed.'
    }), 200
