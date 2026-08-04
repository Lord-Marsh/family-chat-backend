import json
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash

IST_NOW = "2026-08-04T00:00:00+05:30"

users = [
    {
        "_id": "USR001",
        "username": "faseeh",
        "displayName": "Faseeh",
        "email": "adnanfaseehms@gmail.com",
        "userType": "sa",
        "avatar": "",
        "password": generate_password_hash("faseeh12"),
        "createdAt": IST_NOW
    },
    {
        "_id": "USR002",
        "username": "sudhakaran",
        "displayName": "Sudhakaran",
        "email": "sudhakaranmani2003@gmail.com",
        "userType": "a",
        "avatar": "",
        "password": generate_password_hash("sudha123"),
        "createdAt": IST_NOW
    },
    {
        "_id": "USR003",
        "username": "yoganathan",
        "displayName": "Yoganathan",
        "email": "yogan4903@gmail.com",
        "userType": "a",
        "avatar": "",
        "password": generate_password_hash("yogan123"),
        "createdAt": IST_NOW
    },
    {
        "_id": "USR004",
        "username": "hari",
        "displayName": "Hari",
        "email": "harisidh0006@gmail.com",
        "userType": "a",
        "avatar": "",
        "password": generate_password_hash("hari1234"),
        "createdAt": IST_NOW
    }
]

categories = [
    {"_id": "CAT-001", "name": "Food", "icon": "food", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-002", "name": "Snacks", "icon": "snacks", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-003", "name": "Groceries", "icon": "groceries", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-004", "name": "Transport", "icon": "transport", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-005", "name": "Bills", "icon": "bills", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-006", "name": "Recharge", "icon": "recharge", "createdBy": "system", "createdAt": IST_NOW},
    {"_id": "CAT-007", "name": "Other", "icon": "other", "createdBy": "system", "createdAt": IST_NOW},
]

# Generate JSON files
with open('seed_users.json', 'w') as f:
    json.dump(users, f, indent=4)

with open('seed_categories.json', 'w') as f:
    json.dump(categories, f, indent=4)

print("Generated seed_users.json and seed_categories.json")

# If --insert flag is passed, insert directly into MongoDB
if '--insert' in sys.argv:
    try:
        from dotenv import load_dotenv
        import os
        from pymongo import MongoClient

        load_dotenv()
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/sp')
        client = MongoClient(mongo_uri)
        db = client['sp']

        # Insert users (skip if already exist)
        for user in users:
            existing = db.users.find_one({'_id': user['_id']})
            if not existing:
                db.users.insert_one(user)
                print(f"  Inserted user: {user['displayName']} ({user['_id']})")
            else:
                print(f"  Skipped user: {user['displayName']} ({user['_id']}) - already exists")

        # Insert categories (skip if already exist)
        for cat in categories:
            existing = db.categories.find_one({'_id': cat['_id']})
            if not existing:
                db.categories.insert_one(cat)
                print(f"  Inserted category: {cat['name']} ({cat['_id']})")
            else:
                print(f"  Skipped category: {cat['name']} ({cat['_id']}) - already exists")

        print("\nDirect MongoDB insert complete!")
        client.close()
    except Exception as e:
        print(f"\nError inserting into MongoDB: {e}")
        print("Make sure your .env file has the correct MONGO_URI with password.")
