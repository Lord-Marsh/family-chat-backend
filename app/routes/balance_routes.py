from flask import Blueprint, jsonify
from app import get_db
from app.utils.auth import token_required

balance_bp = Blueprint('balances', __name__)

@balance_bp.route('', methods=['GET'])
@token_required
def get_all_balances(current_user_id):
    db = get_db()
    splits = list(db.splits.find({'status': 'active'}))
    users = {u['_id']: u.get('displayName', u['username']) for u in db.users.find()}
    
    pair_balances = {}
    summary = {u_id: {'owes': 0, 'isOwed': 0, 'net': 0} for u_id in users.keys()}
    
    for split in splits:
        for stl in split.get('settlements', []):
            if stl['status'] == 'pending':
                from_id = stl['fromUserId']
                to_id = stl['toUserId']
                amt = stl['amount']
                
                # Pair logic
                pair_key = tuple(sorted([from_id, to_id]))
                if pair_key not in pair_balances:
                    pair_balances[pair_key] = 0
                    
                if from_id == pair_key[0]:
                    pair_balances[pair_key] += amt
                else:
                    pair_balances[pair_key] -= amt
                    
                # Summary logic
                summary[from_id]['owes'] += amt
                summary[from_id]['net'] -= amt
                summary[to_id]['isOwed'] += amt
                summary[to_id]['net'] += amt
                
    balances_list = []
    for pair, net_amt in pair_balances.items():
        if abs(net_amt) > 0.01:
            if net_amt > 0:
                from_user, to_user = pair[0], pair[1]
                amt = net_amt
            else:
                from_user, to_user = pair[1], pair[0]
                amt = abs(net_amt)
                
            balances_list.append({
                'fromUser': {'id': from_user, 'displayName': users.get(from_user, 'Unknown')},
                'toUser': {'id': to_user, 'displayName': users.get(to_user, 'Unknown')},
                'amount': round(amt, 2)
            })
            
    # Round summary
    for k in summary:
        summary[k]['owes'] = round(summary[k]['owes'], 2)
        summary[k]['isOwed'] = round(summary[k]['isOwed'], 2)
        summary[k]['net'] = round(summary[k]['net'], 2)
        
    return jsonify({'balances': balances_list, 'summary': summary}), 200

@balance_bp.route('/summary', methods=['GET'])
@token_required
def get_user_summary(current_user_id):
    db = get_db()
    splits = list(db.splits.find({'status': 'active'}))
    users = {u['_id']: u.get('displayName', u['username']) for u in db.users.find()}
    
    you_owe_dict = {}
    owed_to_you_dict = {}
    
    for split in splits:
        for stl in split.get('settlements', []):
            if stl['status'] == 'pending':
                if stl['fromUserId'] == current_user_id:
                    to_id = stl['toUserId']
                    you_owe_dict[to_id] = you_owe_dict.get(to_id, 0) + stl['amount']
                elif stl['toUserId'] == current_user_id:
                    from_id = stl['fromUserId']
                    owed_to_you_dict[from_id] = owed_to_you_dict.get(from_id, 0) + stl['amount']
                    
    # Net off debts between same users
    for user_id in list(you_owe_dict.keys()):
        if user_id in owed_to_you_dict:
            owe_amt = you_owe_dict[user_id]
            owed_amt = owed_to_you_dict[user_id]
            
            if owe_amt > owed_amt:
                you_owe_dict[user_id] = owe_amt - owed_amt
                del owed_to_you_dict[user_id]
            elif owed_amt > owe_amt:
                owed_to_you_dict[user_id] = owed_amt - owe_amt
                del you_owe_dict[user_id]
            else:
                del you_owe_dict[user_id]
                del owed_to_you_dict[user_id]
                
    you_owe = [
        {'toUser': {'id': uid, 'displayName': users.get(uid, 'Unknown')}, 'amount': round(amt, 2)}
        for uid, amt in you_owe_dict.items()
    ]
    owed_to_you = [
        {'fromUser': {'id': uid, 'displayName': users.get(uid, 'Unknown')}, 'amount': round(amt, 2)}
        for uid, amt in owed_to_you_dict.items()
    ]
    
    net_balance = sum(item['amount'] for item in owed_to_you) - sum(item['amount'] for item in you_owe)
    
    return jsonify({
        'youOwe': you_owe,
        'owedToYou': owed_to_you,
        'netBalance': round(net_balance, 2)
    }), 200
