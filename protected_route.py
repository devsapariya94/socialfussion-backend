from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import datetime
import pymongo
import os
import instaloader
import logging
from googleapiclient.discovery import build
protectedRoute = Blueprint('protectedRoute', __name__)


MONGO_URI = os.getenv('MONGO_URI')
MONGO_DB = os.getenv('MONGO_DB')
MONGO_USERNAME = os.getenv('MONGO_USERNAME')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
APP_SECRET_KEY = os.getenv('APP_SECRET_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
# Setup MongoDB connection and authenticate

# client = MongoClient('localhost', 27017)
client = pymongo.MongoClient(f'mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_URI}/')
db_name= MONGO_DB
db = client.get_database(db_name)

#set up collections
blacklist_token = db['blacklist_token']
instagram_following = db['instagram_following']
youtube_following = db['youtube_following']

# setup logger
logger = logging.getLogger('follow_unfollow_logger')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('protected.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

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
            current_user = data['user_id']  
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# Define the protected route.
@protectedRoute.route('/protected')
@token_required
def protected(current_user):
    return jsonify({'message': 'This is a protected route'}), 200


   
@protectedRoute.route('/addinstafollowing', methods=['POST'])
@token_required
def insta_following(current_user):
    request_data = request.get_json()
    username = request_data['username']
    #check if user exists
    try:
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)
        # add to the database
       
        # if user is already following
        if instagram_following.find_one({'username': username, 'user_id': current_user}):
            return jsonify({'error': 'User is already following'}), 400
        

        instagram_following.insert_one({'username': username, 'user_id': current_user})
        logger.info(f'User {current_user} added {username} to instagram following')
        return jsonify({'message': 'Instagram user added to following'}), 200

    except Exception as e:
        return jsonify({'error': 'Instagram user does not exist or it may be the private account'}), 400

@protectedRoute.route('/addyoutubefollowing', methods=['POST'])
@token_required
def youtube_following(current_user):
    request_data = request.get_json()
    channel_name = request_data['username']  # Renamed 'username' to 'channel_name' to match the first block

    try:
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        search_response = youtube.search().list(
        q=channel_name,
        type='channel',
        part='id'
    ).execute()

        for search_result in search_response.get('items', []):
            if search_result['id']['kind'] == 'youtube#channel':
                channel_id = search_result['id']['channelId']
                break

        youtube_following = db['youtube_following']
        if youtube_following.find_one({'channel_id': channel_id, 'user_id': current_user}):
            return jsonify({'error': 'User is already following'}), 400

        youtube_following.insert_one({'username': channel_name, 'user_id': current_user, 'channel_id': channel_id})
        logger.info(f'User {current_user} added {channel_name} to youtube following')
        return jsonify({'message': 'Youtube user added to following'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to add YouTube user to following'}), 400

