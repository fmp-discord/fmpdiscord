<<<<<<< HEAD
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

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Discord Points Form</title>
        <style>
            /* Resetting default styles */
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
    
            body {
                font-family: Arial, sans-serif;
                background-color: #c1d9dc;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
    
            .container {
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
                padding: 20px;
                width: 100%;
                max-width: 400px; /* Adjusted width for simplicity */
                text-align: center;
                animation: fadeIn 0.6s ease-in-out;
            }
    
            @keyframes fadeIn {
                0% {
                    opacity: 0;
                    transform: translateY(-20px);
                }
    
                100% {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
    
            h1 {
                font-size: 24px;
                color: #333;
                margin-bottom: 20px;
            }
    
            form {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
    
            label {
                font-weight: bold;
                margin-bottom: 5px;
                color: #555;
                display: block;
                text-align: left;
                width: 100%;
            }
    
            input[type="text"],
            input[type="submit"] {
                width: calc(100% - 20px);
                padding: 10px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
    
            input[type="submit"] {
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
                transition: background-color 0.3s;
                margin-top: 10px;
                padding: 12px;
                width: 100%;
                max-width: 200px;
            }
    
            input[type="submit"]:hover {
                background-color: #45a049;
            }
    
            #result {
                margin-top: 20px;
                font-size: 16px;
                color: #c1b8b8;
                text-align: left;
            }
    
            p {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Enter Discord User ID</h1>
            <form id="pointsForm">
                <label for="discord_id">User ID (Discord):</label>
                <input type="number" id="discord_id" name="discord_id" pattern="[0-9]*" placeholder="Enter your Discord User ID" required>
    
                <input type="submit" value="Submit">
            </form>
    
            <div id="result"></div>
        </div>
    
        <script>
            document.getElementById('pointsForm').addEventListener('submit', function (event) {
                event.preventDefault();
    
                const formData = new FormData(event.target);
                const data = {};
                formData.forEach((value, key) => {
                    data[key] = value;
                });
    
                fetch('http://localhost:5000/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => response.json())
                    .then(result => {
                        document.getElementById('result').innerHTML = `
                        <p>${result.message}</p>
                        <p>Total points: ${result.total_points}</p>
                    `;
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
            });
        </script>
    </body>
    </html>
    """

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json  # Assume the request contains JSON data

    discord_id = data['discord_id']
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
=======
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

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Discord Points Form</title>
        <style>
            /* Resetting default styles */
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
    
            body {
                font-family: Arial, sans-serif;
                background-color: #c1d9dc;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
    
            .container {
                background-color: #ffffff;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.5);
                padding: 20px;
                width: 100%;
                max-width: 400px; /* Adjusted width for simplicity */
                text-align: center;
                animation: fadeIn 0.6s ease-in-out;
            }
    
            @keyframes fadeIn {
                0% {
                    opacity: 0;
                    transform: translateY(-20px);
                }
    
                100% {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
    
            h1 {
                font-size: 24px;
                color: #333;
                margin-bottom: 20px;
            }
    
            form {
                display: flex;
                flex-direction: column;
                align-items: center;
            }
    
            label {
                font-weight: bold;
                margin-bottom: 5px;
                color: #555;
                display: block;
                text-align: left;
                width: 100%;
            }
    
            input[type="text"],
            input[type="submit"] {
                width: calc(100% - 20px);
                padding: 10px;
                margin: 8px 0;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 14px;
                transition: border-color 0.3s;
            }
    
            input[type="submit"] {
                background-color: #4CAF50;
                color: white;
                border: none;
                cursor: pointer;
                transition: background-color 0.3s;
                margin-top: 10px;
                padding: 12px;
                width: 100%;
                max-width: 200px;
            }
    
            input[type="submit"]:hover {
                background-color: #45a049;
            }
    
            #result {
                margin-top: 20px;
                font-size: 16px;
                color: #c1b8b8;
                text-align: left;
            }
    
            p {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Enter Discord User ID</h1>
            <form id="pointsForm">
                <label for="discord_id">User ID (Discord):</label>
                <input type="number" id="discord_id" name="discord_id" pattern="[0-9]*" placeholder="Enter your Discord User ID" required>
    
                <input type="submit" value="Submit">
            </form>
    
            <div id="result"></div>
        </div>
    
        <script>
            document.getElementById('pointsForm').addEventListener('submit', function (event) {
                event.preventDefault();
    
                const formData = new FormData(event.target);
                const data = {};
                formData.forEach((value, key) => {
                    data[key] = value;
                });
    
                fetch('http://localhost:5000/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                })
                    .then(response => response.json())
                    .then(result => {
                        document.getElementById('result').innerHTML = `
                        <p>${result.message}</p>
                        <p>Total points: ${result.total_points}</p>
                    `;
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
            });
        </script>
    </body>
    </html>
    """

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json  # Assume the request contains JSON data

    discord_id = data['discord_id']
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
>>>>>>> ee2e2b3c3f49cb7edf0884013ef9ae679ec00539
