from flask import Blueprint, jsonify
from app import get_db
from app.utils.auth import token_required
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

analytics_bp = Blueprint('analytics', __name__)
IST = pytz.timezone('Asia/Kolkata')

@analytics_bp.route('', methods=['GET'])
@token_required
def get_expense_analytics(current_user_id):
    db = get_db()
    
    query = {
        '$or': [{'paidBy.userId': current_user_id}, {'splitAmong.userId': current_user_id}],
        'status': {'$in': ['active', 'settled']}
    }
    
    splits = list(db.splits.find(query).sort('createdAt', -1))
    
    total_spent_by_user = 0
    total_group_spent = 0
    
    category_totals = defaultdict(float)
    daily_totals = defaultdict(float)
    weekly_totals = defaultdict(float)
    monthly_totals = defaultdict(float)
    
    sorted_by_amount = sorted(splits, key=lambda x: x.get('totalAmount', 0), reverse=True)
    top_expenses = sorted_by_amount[:5]
    
    for split in splits:
        amt = float(split.get('totalAmount', 0))
        total_group_spent += amt
        
        user_share = 0
        for p in split.get('splitAmong', []):
            if p.get('userId') == current_user_id:
                user_share = float(p.get('share', 0))
                break
        
        if user_share > 0:
            total_spent_by_user += user_share
            cat = split.get('category') or 'Other'
            category_totals[cat] += user_share
            
            created_at = split.get('createdAt')
            if created_at:
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                
                day_key = created_at.strftime('%Y-%m-%d')
                daily_totals[day_key] += user_share
                
                month_key = created_at.strftime('%Y-%m')
                monthly_totals[month_key] += user_share
                
                week_key = created_at.strftime('%Y-W%V')
                weekly_totals[week_key] += user_share
    
    pie_data = [{'name': k, 'value': round(v, 2)} for k, v in category_totals.items()]
    pie_data = sorted(pie_data, key=lambda x: x['value'], reverse=True)
    
    daily_data = [{'date': k, 'amount': round(v, 2)} for k, v in sorted(daily_totals.items())]
    monthly_data = [{'month': k, 'amount': round(v, 2)} for k, v in sorted(monthly_totals.items())]
    weekly_data = [{'week': k, 'amount': round(v, 2)} for k, v in sorted(weekly_totals.items())]
    
    top_expenses_mapped = []
    users = {u['_id']: u.get('displayName', u['username']) for u in db.users.find()}
    for s in top_expenses:
        top_expenses_mapped.append({
            'id': s['_id'],
            'description': s.get('description', 'Unknown'),
            'category': s.get('category', 'Other'),
            'amount': s.get('totalAmount', 0),
            'date': s.get('createdAt').isoformat() if isinstance(s.get('createdAt'), datetime) else s.get('createdAt')
        })
    
    return jsonify({
        'overview': {
            'personalTotal': round(total_spent_by_user, 2),
            'groupTotal': round(total_group_spent, 2),
            'totalTransactions': len(splits)
        },
        'categories': pie_data,
        'daily': daily_data,
        'weekly': weekly_data,
        'monthly': monthly_data,
        'topExpenses': top_expenses_mapped
    }), 200
