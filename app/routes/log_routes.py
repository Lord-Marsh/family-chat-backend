from flask import Blueprint, request, jsonify
from app import get_db
from app.utils.auth import token_required, sa_required
from math import ceil

log_bp = Blueprint('logs', __name__)

def paginate_query(collection, query, page, limit, sort_by):
    skip = (page - 1) * limit
    cursor = collection.find(query).sort(sort_by, -1).skip(skip).limit(limit)
    items = list(cursor)
    total = collection.count_documents(query)
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'limit': limit,
        'totalPages': ceil(total / limit) if limit > 0 else 0
    }

@log_bp.route('/login', methods=['GET'])
@sa_required
def get_login_logs(current_user_id, current_user):
    db = get_db()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    user_id = request.args.get('userId')
    
    query = {}
    if user_id:
        query['userId'] = user_id
        
    result = paginate_query(db.login_logs, query, page, limit, 'timestamp')
    return jsonify(result), 200

@log_bp.route('/email', methods=['GET'])
@sa_required
def get_email_logs(current_user_id, current_user):
    db = get_db()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    status = request.args.get('status')
    
    query = {}
    if status:
        query['status'] = status
        
    result = paginate_query(db.email_logs, query, page, limit, 'timestamp')
    return jsonify(result), 200

@log_bp.route('/activity', methods=['GET'])
@sa_required
def get_activity_logs(current_user_id, current_user):
    db = get_db()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    action = request.args.get('action')
    user_id = request.args.get('userId')
    
    query = {}
    if action:
        query['action'] = action
    if user_id:
        query['userId'] = user_id
        
    result = paginate_query(db.activity_logs, query, page, limit, 'timestamp')
    return jsonify(result), 200
