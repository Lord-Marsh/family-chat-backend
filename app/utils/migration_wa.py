def run_wa_migration(db):
    import re
    try:
        # Update Faseeh
        db.users.update_one(
            {"username": {"$regex": re.compile("^faseeh$", re.IGNORECASE)}},
            {"$set": {"phone": "918056357572"}}
        )
        # Update Hari
        db.users.update_one(
            {"username": {"$regex": re.compile("^hari$", re.IGNORECASE)}},
            {"$set": {"phone": "917806847970"}}
        )
        # Update Sudhakaran
        db.users.update_one(
            {"username": {"$regex": re.compile("^sudhakaran$", re.IGNORECASE)}},
            {"$set": {"phone": "919597718611"}}
        )
        # Update Yoganathan
        db.users.update_one(
            {"username": {"$regex": re.compile("^yoganathan$", re.IGNORECASE)}},
            {"$set": {"phone": "918072033891"}}
        )
        print("WhatsApp migration complete.")
    except Exception as e:
        print(f"WhatsApp migration failed: {e}")
