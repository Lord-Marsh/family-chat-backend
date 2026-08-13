def run_migration(db):
    split_id = 'SPL-20260812-213817-201A'
    split = db.splits.find_one({'_id': split_id})
    if not split:
        return
        
    users = list(db.users.find({}))
    faseeh_id = next((u['_id'] for u in users if u.get('displayName', u.get('username', '')).lower() == 'faseeh'), None)
    sudhakaran_id = next((u['_id'] for u in users if u.get('displayName', u.get('username', '')).lower() == 'sudhakaran'), None)
    hari_id = next((u['_id'] for u in users if u.get('displayName', u.get('username', '')).lower() == 'hari'), None)
    
    if not faseeh_id:
        return
        
    settlements = split.get('settlements', [])
    updated = False
    
    # Try to find existing settlements and add amounts
    found_sudhakaran = False
    found_hari = False
    
    for stl in settlements:
        if stl['fromUserId'] == sudhakaran_id and stl['toUserId'] == faseeh_id:
            if not stl.get('_migrated'):
                stl['amount'] += 15
                stl['_migrated'] = True
                updated = True
            found_sudhakaran = True
        elif stl['fromUserId'] == hari_id and stl['toUserId'] == faseeh_id:
            if not stl.get('_migrated'):
                stl['amount'] += 25
                stl['_migrated'] = True
                updated = True
            found_hari = True
            
    # If they didn't exist in settlements at all, append new ones
    if not found_sudhakaran and sudhakaran_id:
        settlements.append({
            'id': f"STL-MIG-1",
            'fromUserId': sudhakaran_id,
            'toUserId': faseeh_id,
            'amount': 15,
            'status': 'pending',
            'paidAt': None,
            'note': 'Manual Adjustment',
            'markedBy': None,
            'markedAt': None,
            '_migrated': True
        })
        updated = True
        
    if not found_hari and hari_id:
        settlements.append({
            'id': f"STL-MIG-2",
            'fromUserId': hari_id,
            'toUserId': faseeh_id,
            'amount': 25,
            'status': 'pending',
            'paidAt': None,
            'note': 'Manual Adjustment',
            'markedBy': None,
            'markedAt': None,
            '_migrated': True
        })
        updated = True
        
    if updated:
        db.splits.update_one({'_id': split_id}, {'$set': {'settlements': settlements}})
