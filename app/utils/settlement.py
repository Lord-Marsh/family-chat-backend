def calculate_settlements(paid_by, split_among):
    net_balances = {}
    
    # Calculate what everyone paid
    for payer in paid_by:
        user_id = payer['userId']
        net_balances[user_id] = net_balances.get(user_id, 0) + float(payer['amount'])
        
    # Subtract what everyone owes
    for share in split_among:
        user_id = share['userId']
        net_balances[user_id] = net_balances.get(user_id, 0) - float(share['share'])
        
    # Separate into debtors and creditors
    debtors = []
    creditors = []
    
    for user_id, amount in net_balances.items():
        if amount < -0.01:
            debtors.append({'userId': user_id, 'amount': amount})
        elif amount > 0.01:
            creditors.append({'userId': user_id, 'amount': amount})
            
    # Sort by amount (ascending for debtors, descending for creditors)
    debtors.sort(key=lambda x: x['amount'])
    creditors.sort(key=lambda x: x['amount'], reverse=True)
    
    settlements = []
    d_idx = 0
    c_idx = 0
    
    settlement_counter = 1
    
    while d_idx < len(debtors) and c_idx < len(creditors):
        debtor = debtors[d_idx]
        creditor = creditors[c_idx]
        
        # Debtor amount is negative, so we use abs()
        debt_amount = abs(debtor['amount'])
        credit_amount = creditor['amount']
        
        settle_amount = min(debt_amount, credit_amount)
        
        settle_amount = round(settle_amount)
        
        if settle_amount > 0:
            settlements.append({
                'id': f'STL-{settlement_counter:03d}',
                'fromUserId': debtor['userId'],
                'toUserId': creditor['userId'],
                'amount': settle_amount,
                'status': 'pending',
                'paidAt': None,
                'note': '',
                'markedBy': None,
                'markedAt': None
            })
            settlement_counter += 1
            
        debtors[d_idx]['amount'] += settle_amount
        creditors[c_idx]['amount'] -= settle_amount
        
        if abs(debtors[d_idx]['amount']) < 0.01:
            d_idx += 1
        if creditors[c_idx]['amount'] < 0.01:
            c_idx += 1
            
    return settlements
