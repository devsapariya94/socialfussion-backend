from flask import Blueprint, request, jsonify
from functools import wraps
import jwt
import datetime
import pymongo
import os
import instaloader
import logging
from googleapiclient.discovery import build
from datetime import datetime
from youtube_video_retivive import scrape_and_update
from insta_post_retriving import scrape_data
import threading

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
# client = pymongo.MongoClient('mongodb://localhost:27017/')
db_name= MONGO_DB
db = client.get_database(db_name)

#set up collections
blacklist_token = db['blacklist_token']
instagram_following = db['instagram_following']
youtube_following = db['youtube_following']
youtube_creators = db['youtube_creators']
instagram_creators = db['instagram_creators']

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
        print("1")
        print(username)
        loader = instaloader.Instaloader()
        profile = instaloader.Profile.from_username(loader.context, username)
        # add to the database
       
        # if user is already following
        if instagram_following.find_one({'username': username, 'user_id': current_user}):
            return jsonify({'error': 'User is already following'}), 400
        
        print("2")
        instagram_following.insert_one({'username': username, 'user_id': current_user})
        #if username not in instagram_creators then add it
        if not instagram_creators.find_one({'username': username}): 
            instagram_creators.insert_one({'username': username})
        print("3")
        #start the thread to scrape the posts
        # thread = threading.Thread(target=scrape_data, args=(username,))
        # thread.start()

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

        #if username not in youtube_creators then add it
        if not youtube_creators.find_one({'channel_id': channel_id}): 
            youtube_creators.insert_one({'channel_id': channel_id})
            
        logger.info(f'User {current_user} added {channel_name} to youtube following')
        #start the thread to scrape the videos
        # thread = threading.Thread(target=scrape_and_update)
        # thread.start()

        return jsonify({'message': 'Youtube user added to following'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to add YouTube user to following'}), 400

@protectedRoute.route('/all', methods=['GET'])
@token_required
def all_post(current_user):
    instagram_posts = db['instagram_posts']
    youtube_videos = db['youtube_videos']
    insta_following = db['instagram_following']
    youtube_following = db['youtube_following']

    # Get all the Instagram posts of the users the current user is following
    all_instagram_posts = []
    for user in insta_following.find({'user_id': current_user}):
        posts = instagram_posts.find({'username': user['username']})
        for post in posts:
            if isinstance(post['timestamp'], str):
                post['timestamp'] = datetime.strptime(post['timestamp'], "%Y-%m-%d %H:%M:%S")
            all_instagram_posts.append(post)

    # Get all the YouTube videos of the users the current user is following
    all_youtube_videos = []
    for user in youtube_following.find({'user_id': current_user}):
        videos = youtube_videos.find({'channel_id': user['channel_id']})
        for video in videos:
            if isinstance(video['timestamp'], str):
                video['timestamp'] = datetime.strptime(video['timestamp'], "%Y-%m-%d %H:%M:%S")
            all_youtube_videos.append(video)

    # Combine the two lists and sort by timestamp
    all_posts = []
    for post in all_instagram_posts:
        all_posts.append(['instagram', post])
    for post in all_youtube_videos:
        all_posts.append(['youtube', post])
    
    all_posts.sort(key=lambda x: x[1]['timestamp'], reverse=True)
    #send the [["instagrm",shortcode],["youtube","video_id"]]
    main =[]
    for post in all_posts:
        print("***********************")
        print(type(post))
        print(post)
        print("*********************")
        if post[0]=="instagram":
            main.append(["instagram",post[1].get("shortcode")])
        if post[0]=="youtube":
            main.append(["youtube",post[1].get("video_id")])
    print(main)
    return jsonify({'all_posts': main}), 200


@protectedRoute.route('/instagram/posts', methods=['GET'])
@token_required
def instagram_posts(current_user):
    instagram_posts = db['instagram_posts']
    insta_following = db['instagram_following']

    all_instagram_posts = []
    for user in insta_following.find({'user_id': current_user}):
        posts = instagram_posts.find({'username': user['username']})
        for post in posts:
            if isinstance(post['timestamp'], str):
                post['timestamp'] = datetime.strptime(post['timestamp'], "%Y-%m-%d %H:%M:%S")
            all_instagram_posts.append(post)

    all_instagram_posts.sort(key=lambda x: x['timestamp'], reverse=True)
    main =[]
    for post in all_instagram_posts:
        main.append(post.get("shortcode"))
    return jsonify({'all_instagram_posts': main}), 200


@protectedRoute.route('/youtube/videos', methods=['GET'])
@token_required
def youtube_videos(current_user):
    youtube_videos = db['youtube_videos']
    youtube_following = db['youtube_following']

    all_youtube_videos = []
    for user in youtube_following.find({'user_id': current_user}):
        videos = youtube_videos.find({'channel_id': user['channel_id']})
        for video in videos:
            if isinstance(video['timestamp'], str):
                video['timestamp'] = datetime.strptime(video['timestamp'], "%Y-%m-%d %H:%M:%S")
            all_youtube_videos.append(video)
    main =[]
    for post in all_youtube_videos:
        main.append(post.get("video_id"))
    all_youtube_videos.sort(key=lambda x: x['timestamp'], reverse=True)
    return jsonify({'all_youtube_videos': main}), 200

