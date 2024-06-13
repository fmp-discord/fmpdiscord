from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app, resources={r"/submit": {"origins": "https://fmp-discord.github.io"}})

# MongoDB connection URI for MongoDB Atlas cluster
uri = "mongodb+srv://Bijay:bijay%40123@cluster0.hpl6qfx.mongodb.net/db_discord?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
    print("Connected to the database.")
except Exception as e:
    print(e)

# Database and collection names
db = client.db_discord
users_collection = db.tbl_discord

# Ensure the collection exists, create it if it doesn't
if "tbl_discord" not in db.list_collection_names():
    users_collection = db.create_collection("tbl_discord")
else:
    users_collection = db.tbl_discord

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json  # Assume the request contains JSON data

    discord_id = int(data['discord_id'])  # Convert to integer
    username = data.get('username')
    server = data.get('server')
    cookies = data.get('cookies', [])
    current_time = datetime.now()
    
    user = users_collection.find_one({"userid": discord_id})
    
    if user:
        last_visit = user['updatedat']
        if current_time < last_visit + timedelta(hours=1):
            time_remaining = last_visit + timedelta(hours=1) - current_time
            print(f"User {discord_id} needs to wait for {time_remaining.seconds // 60} more minutes.")
            return jsonify({
                "message": f"Come back after {time_remaining.seconds // 60} minutes to get more points.",
                "total_points": user['points']
            })
        else:
            users_collection.update_one(
                {"userid": discord_id}, 
                {"$set": {"updatedat": current_time}, "$inc": {"points": 2}}
            )
            user = users_collection.find_one({"userid": discord_id})
            print(f"Updated user {discord_id} at {current_time}. Total points: {user['points']}")
            return jsonify({
                "message": "Thanks! You got 2 points.",
                "total_points": user['points']
            })
    else:
        new_user = {
            "username": username or f"user_{discord_id}",
            "userid": discord_id,
            "createdat": current_time,
            "updatedat": current_time,
            "points": 2,
            "server": server,
            "cookies": cookies
        }
        users_collection.insert_one(new_user)
        print(f"Inserted new user {discord_id} at {current_time}. Total points: 2")
        return jsonify({
            "message": "Thanks! You got 2 points.",
            "total_points": 2
        })

if __name__ == '__main__':
    app.run(debug=True)
