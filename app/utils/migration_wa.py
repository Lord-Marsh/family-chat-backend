def run_wa_migration(db):
    try:
        # Update Faseeh
        db.users.update_one(
            {"username": "Faseeh"},
            {"$set": {"phone": "918056357572"}}
        )
        # Update Hari
        db.users.update_one(
            {"username": "Hari"},
            {"$set": {"phone": "917806847970"}}
        )
        # Update Sudhakaran
        db.users.update_one(
            {"username": "Sudhakaran"},
            {"$set": {"phone": "919597718611"}}
        )
        # Update Yoganathan
        db.users.update_one(
            {"username": "Yoganathan"},
            {"$set": {"phone": "918072033891"}}
        )
        print("WhatsApp migration complete.")
    except Exception as e:
        print(f"WhatsApp migration failed: {e}")
