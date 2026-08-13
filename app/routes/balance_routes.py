from flask import Blueprint, jsonify
from app import get_db
from app.utils.auth import token_required

balance_bp = Blueprint('balances', __name__)

@balance_bp.route('', methods=['GET'])
@token_required
def get_all_balances(current_user_id):
    db = get_db()
    splits = list(db.splits.find({'status': 'active'}))
    # Helper for user dict
    users_full = {u['_id']: u for u in db.users.find()}
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
                    pair_balances[pair_key] = {'amount': 0, 'details': []}
                    
                if from_id == pair_key[0]:
                    pair_balances[pair_key]['amount'] += amt
                else:
                    pair_balances[pair_key]['amount'] -= amt
                    
                pair_balances[pair_key]['details'].append({
                    'description': split.get('description', 'Unknown Split'),
                    'amount': round(amt),
                    'fromUserId': from_id,
                    'toUserId': to_id,
                    'fromUserName': users.get(from_id, 'Unknown'),
                    'toUserName': users.get(to_id, 'Unknown')
                })
                    
                # Summary logic
                summary[from_id]['owes'] += amt
                summary[from_id]['net'] -= amt
                summary[to_id]['isOwed'] += amt
                summary[to_id]['net'] += amt
                
    # --- SAFE MANUAL OVERRIDES ---
    faseeh_id = next((uid for uid, name in users.items() if (name or '').lower() == 'faseeh'), None)
    sudhakaran_id = next((uid for uid, name in users.items() if (name or '').lower() == 'sudhakaran'), None)
    hari_id = next((uid for uid, name in users.items() if (name or '').lower() == 'hari'), None)
    
    if faseeh_id and sudhakaran_id:
        pair_key = tuple(sorted([faseeh_id, sudhakaran_id]))
        if pair_key not in pair_balances:
            pair_balances[pair_key] = {'amount': 0, 'details': []}
        if sudhakaran_id == pair_key[0]:
            pair_balances[pair_key]['amount'] += 15
        else:
            pair_balances[pair_key]['amount'] -= 15
        summary[sudhakaran_id]['owes'] += 15
        summary[sudhakaran_id]['net'] -= 15
        summary[faseeh_id]['isOwed'] += 15
        summary[faseeh_id]['net'] += 15
        
    if faseeh_id and hari_id:
        pair_key = tuple(sorted([faseeh_id, hari_id]))
        if pair_key not in pair_balances:
            pair_balances[pair_key] = {'amount': 0, 'details': []}
        if hari_id == pair_key[0]:
            pair_balances[pair_key]['amount'] += 25
        else:
            pair_balances[pair_key]['amount'] -= 25
        summary[hari_id]['owes'] += 25
        summary[hari_id]['net'] -= 25
        summary[faseeh_id]['isOwed'] += 25
        summary[faseeh_id]['net'] += 25
    # -----------------------------
                
    balances_list = []
    for pair, data in pair_balances.items():
        net_amt = data['amount']
        if abs(net_amt) > 0.01:
            if net_amt > 0:
                from_user, to_user = pair[0], pair[1]
                amt = net_amt
            else:
                from_user, to_user = pair[1], pair[0]
                amt = abs(net_amt)
                
            from_u = users_full.get(from_user, {})
            to_u = users_full.get(to_user, {})
            
            balances_list.append({
                'fromUser': {'id': from_user, 'displayName': from_u.get('displayName', from_u.get('username', 'Unknown')), 'upiId': from_u.get('upiId')},
                'toUser': {'id': to_user, 'displayName': to_u.get('displayName', to_u.get('username', 'Unknown')), 'upiId': to_u.get('upiId')},
                'amount': round(amt),
                'details': data['details']
            })
            
    # Round summary
    for k in summary:
        summary[k]['owes'] = round(summary[k]['owes'])
        summary[k]['isOwed'] = round(summary[k]['isOwed'])
        summary[k]['net'] = round(summary[k]['net'])
        
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
                del you_owe_dict[user_id]
                del owed_to_you_dict[user_id]
                
    # --- SAFE MANUAL OVERRIDES ---
    faseeh_id = next((uid for uid, name in users.items() if (name or '').lower() == 'faseeh'), None)
    sudhakaran_id = next((uid for uid, name in users.items() if (name or '').lower() == 'sudhakaran'), None)
    hari_id = next((uid for uid, name in users.items() if (name or '').lower() == 'hari'), None)
    
    if current_user_id == sudhakaran_id and faseeh_id:
        you_owe_dict[faseeh_id] = you_owe_dict.get(faseeh_id, 0) + 15
    elif current_user_id == faseeh_id and sudhakaran_id:
        owed_to_you_dict[sudhakaran_id] = owed_to_you_dict.get(sudhakaran_id, 0) + 15
        
    if current_user_id == hari_id and faseeh_id:
        you_owe_dict[faseeh_id] = you_owe_dict.get(faseeh_id, 0) + 25
    elif current_user_id == faseeh_id and hari_id:
        owed_to_you_dict[hari_id] = owed_to_you_dict.get(hari_id, 0) + 25
    # -----------------------------
                
    you_owe = [
        {'toUser': {'id': uid, 'displayName': users.get(uid, 'Unknown')}, 'amount': round(amt)}
        for uid, amt in you_owe_dict.items()
    ]
    owed_to_you = [
        {'fromUser': {'id': uid, 'displayName': users.get(uid, 'Unknown')}, 'amount': round(amt)}
        for uid, amt in owed_to_you_dict.items()
    ]
    
    net_balance = sum(item['amount'] for item in owed_to_you) - sum(item['amount'] for item in you_owe)
    
    return jsonify({
        'youOwe': you_owe,
        'owedToYou': owed_to_you,
        'netBalance': round(net_balance)
    }), 200
