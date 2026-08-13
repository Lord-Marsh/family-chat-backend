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
    
    for stl in settlements:
        if stl['fromUserId'] == sudhakaran_id and stl['toUserId'] == faseeh_id:
            if stl.get('_migrated'):
                stl['amount'] -= 15
                del stl['_migrated']
                updated = True
        elif stl['fromUserId'] == hari_id and stl['toUserId'] == faseeh_id:
            if stl.get('_migrated'):
                stl['amount'] -= 25
                del stl['_migrated']
                updated = True
                
    # Also remove any entirely fabricated migrated settlements if we created them
    new_settlements = []
    for stl in settlements:
        if stl.get('_migrated') and stl.get('id', '').startswith('STL-MIG'):
            updated = True
            continue
        new_settlements.append(stl)
        
    if updated:
        db.splits.update_one({'_id': split_id}, {'$set': {'settlements': new_settlements}})
