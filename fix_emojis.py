from pymongo import MongoClient

client = MongoClient('mongodb://127.0.0.1:27017/sp')
db = client.get_database('sp')

emoji_map = {
    'CAT-001': '🍔',
    'CAT-002': '🍿',
    'CAT-003': '🛒',
    'CAT-004': '🚗',
    'CAT-005': '📄',
    'CAT-006': '📱',
    'CAT-007': '📦'
}

for cat_id, emoji in emoji_map.items():
    db.categories.update_one({'_id': cat_id}, {'$set': {'icon': emoji}})

print('Updated category icons to emojis!')
