from flask import Flask, Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import dotenv
import os
import pymongo
import hashlib
import jwt
import datetime
from datetime import timedelta
from functools import wraps
from flask_login import logout_user 
import logging

dotenv.load_dotenv()

authRoute = Blueprint('authRoute', __name__)

MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_USERNAME = os.getenv('MONGO_USERNAME')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
APP_SECRET_KEY = os.getenv('APP_SECRET_KEY')
# Setup MongoDB connection and authenticate

# client = MongoClient('localhost', 27017)
# client = pymongo.MongoClient(f'mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_URI}/')
client = pymongo.MongoClient('mongodb://localhost:27017/')
db_name= MONGO_DB
db = client.get_database(db_name)

#set up collections
users = db['users']
blacklist_token = db['blacklist_token']

# Setup Flask app and login manager
app = Flask(__name__)
login_manager = LoginManager(app)


#set up auth logger
logger = logging.getLogger('auth')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('auth.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

def generate_token(user):
    payload = {
        'user_id': user['username'],  # You can customize the payload as needed
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # Token expiration time
    }
    token = jwt.encode(payload,APP_SECRET_KEY, algorithm='HS256')
    return token

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        # Check if the token is blacklisted
        if blacklist_token.find_one({'token': token}):
            return jsonify({'error': 'Token is invalid'}), 401

        try:
            data = jwt.decode(token, APP_SECRET_KEY, algorithms=['HS256'])
            current_user = data['user_id']  # Set the current user based on the token payload
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated



@login_manager.user_loader
def load_user(user_id):
    user = users.find_one({'_id': ObjectId(user_id)})
    return user

@authRoute.route('/register', methods=['POST'])
def register():
    request_data = request.get_json()
    username = request_data['username']
    password = request_data['password']
    email = request_data['email']
    name = request_data['name']

    #hash the password
    password = hashlib.sha256(password.encode()).hexdigest()

    #check if user exists
    if users.find_one({'username': username}):
        return jsonify({'error': 'Username already exists'}), 400

    #check if email exists
    if users.find_one({'email': email}):
        return jsonify({'error': 'Email already exists'}), 400

    #create the user
    new_user = {
        'username': username,
        'password': password,
        'email': email,
        'name': name
    }

    #insert the user
    users.insert_one(new_user)
    logger.info(f'User {username} created')
    token = generate_token(new_user)
    return jsonify({'message': 'User created', 'token': token}), 200


@authRoute.route('/login', methods=['POST'])
def login():
    request_data = request.get_json()
    username = request_data['username']
    password = request_data['password']

    #check if user exists
    if not users.find_one({'username': username}):
        return jsonify({'error': 'Username does not exist'}), 400

    #check if password is correct
    password = hashlib.sha256(password.encode()).hexdigest()

    if users.find_one({'username': username, 'password': password}):
        token = generate_token(users.find_one({'username': username}))
        logger.info(f'User {username} logged in')
        return jsonify({'message': 'User logged in', 'token': token}), 200
    else:
        return jsonify({'error': 'Incorrect password'}), 400


@authRoute.route('/logout')
@token_required
def logout(current_user):
    # Get the existing token
    token = request.headers.get('Authorization')

    # Add the token to the blacklist collection
    blacklist_token.insert_one({'token': token})

    try:
        # Decode the existing token to check its validity
        jwt.decode(token, APP_SECRET_KEY, algorithms=['HS256'])

        # If the token is valid, issue a new token with a longer expiration time (e.g., 30 minutes)
        payload = {
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
        }
        

        logger.info(f'User {current_user} logged out')

        return jsonify({'message': 'User logged out'}), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token has already expired'}), 400
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 400

