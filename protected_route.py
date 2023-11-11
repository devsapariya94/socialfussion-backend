from flask import Blueprint, request, jsonify,make_response
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
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fpdf import FPDF



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
users = db['users']

# setup logger
logger = logging.getLogger('follow_unfollow_logger')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('protected.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

#setup email 
sender_email = "pdfdummy5@gmail.com"
sender_password = "xeat hkem vijr hyna"
smtp_server = "smtp.gmail.com"
smtp_port = 587


#temp db
mongo_client2 = pymongo.MongoClient('mongodb+srv://soni3112chitt:1234567890@cluster0.lnv9sw0.mongodb.net/')
db2 = mongo_client2['project1']
login_logout_collection = db2['login_logout_data']
    

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
        thread = threading.Thread(target=scrape_data, args=(username,))
        thread.start()

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
            #start the thread
            thread = threading.Thread(target=scrape_and_update)
            thread.start()
            
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


def get_login_logout_data(user_id):
    data = login_logout_collection.find({'user_id': int(user_id)})
    data_list = list(data)
    print("Login Logout Data:", data_list)  # Add this line to print the retrieved data
    return data_list



def generate_heatmap_pdf(login_logout_data, output_file="heatmap.png"):
    # Extract day of the week and hour of the day from MongoDB login times
    login_times = [row['login_time'] for row in login_logout_data]
    login_times = [datetime.strptime(login_time, '%Y-%m-%d %H:%M:%S') for login_time in login_times]

    day_of_week = [login_time.weekday() for login_time in login_times]
    hour_of_day = [login_time.hour for login_time in login_times]

    # Create a 2D histogram (heatmap)
    heatmap, xedges, yedges = np.histogram2d(day_of_week, hour_of_day, bins=[7, 24])
    extent = [0, 7, 0, 24]

    print("Day of Week:", day_of_week)  # Add this line to print day of the week
    print("Hour of Day:", hour_of_day)  # Add this line to print the hour of the day

    # Create a heatmap of user activity
    plt.figure(figsize=(12, 6))
    plt.imshow(heatmap.T, extent=extent, origin='lower', cmap='YlGnBu')
    plt.colorbar()
    plt.xticks(range(7), ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    plt.xlabel("Day of the Week")
    plt.ylabel("Hour of the Day")
    plt.title("Heatmap of User Activity")
    plt.savefig(output_file)  # Save the heatmap as the specified output file


def generate_combined_analysis_pdf(user_id):
    login_logout_data = get_login_logout_data(user_id)

    if not login_logout_data:
        return  # No data found for the user, so no need to generate a PDF

    # Accumulate login times and session durations for all entries
    login_times = []
    session_durations = []

    for entry in login_logout_data:
        login_time = datetime.strptime(entry['login_time'], '%Y-%m-%d %H:%M:%S')
        logout_time = datetime.strptime(entry['logout_time'], '%Y-%m-%d %H:%M:%S')
       
        if login_time <= logout_time:
            session_duration = (logout_time - login_time).total_seconds() / 3600
            login_times.append(login_time)
            session_durations.append(session_duration)
        

    if not login_times or not session_durations:
        return  # No valid session data to plot

    # Create a PDF document
    pdf = FPDF()
    pdf.add_page()

    # Set the background color to hex color #001B37 (dark blue)
    pdf.set_fill_color(0, 27, 55)  # Dark blue color
    pdf.rect(0, 0, 210, 297, "F")  # Filled rectangle for the background

    # Add a sample logo image to the top left corner
    pdf.image("logo.png", x=10, y=10, w=50)  # Adjust the x, y, and w values as needed

    # Set font and size for description text
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(255, 255, 255)  # Text color (white)

    # Calculate the coordinates to center the description text
    text_x = (210 - pdf.get_string_width("User Activity Over Time")) / 2
    pdf.set_x(text_x)
    pdf.cell(200, 10, "User Activity Over Time", ln=True, align="C")

    # Add description for the user activity chart
    pdf.multi_cell(0, 10, "This chart shows the user's activity over time, including login and logout times.", align="L")
    pdf.ln(10)  # Move to the next line

    # Call the function to generate the user activity time series line chart
    generate_user_activity_pdf(pdf, login_times, session_durations)

    # Calculate the coordinates to center the graph
    graph_x = (210 - 190) / 2
    pdf.image("user_activity_chart.png", x=graph_x, y=40, w=190)

    # Add a border to the page
    pdf.set_draw_color(255, 255, 255)  # Border color (white)
    pdf.set_line_width(1)  # Border line width
    pdf.rect(5.0, 5.0, 200.0, 287.0)  # Rectangle coordinates and dimensions

    # Generate the heatmap and describe it
    generate_heatmap_pdf(login_logout_data, output_file="heatmap.png")
    pdf.add_page()
    pdf.set_fill_color(0, 27, 55)  # Dark blue color
    pdf.rect(0, 0, 210, 297, "F")
    pdf.multi_cell(0, 10, "This heatmap illustrates the user's activity over the course of a week, highlighting the busiest times of each day.", align="L")
    pdf.image("heatmap.png", x=10, y=10, w=190)
    pdf.set_font("Arial", size=12)
    pdf.set_text_color(255, 255, 255)
    

    # Save the combined analysis PDF
    pdf.output("analysis.pdf")



def generate_user_activity_pdf(pdf, login_times, session_durations):
    # Create a time series line chart for session durations
    plt.figure(figsize=(12, 6))
    plt.plot(login_times, session_durations)
    plt.xlabel("Time")
    plt.ylabel("Session Duration (hours)")
    plt.title("User Activity Over Time")
    
    # Save the chart to an image file
    plt.savefig("user_activity_chart.png")


@protectedRoute.route('/analysis', methods=['GET'])
@token_required
def analysis(current_user):
    users_collection = db2['users']
    user_id = 1
    request_pdf = True

    if user_id:
        user = users.find_one({"username": current_user})

        if user:
            user_email = user['email']

            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"{timestamp} - User with ID {user_id} (Email: {user_email}) made a request. Request successful.")
            result = f"Request logged for user ID: {user_id}"

            if request_pdf:
                generate_combined_analysis_pdf(user_id)

                subject = "Combined PDF Attachment"
                body = "Hello, please find the attached combined PDF."

                message = MIMEMultipart()
                message["From"] = sender_email
                message["To"] = user_email
                message["Subject"] = subject

                message.attach(MIMEText(body, "plain"))

                # Attach the combined PDF
                with open("analysis.pdf", "rb") as pdf_file:
                    attach = MIMEApplication(pdf_file.read(), _subtype="pdf")
                    attach.add_header("Content-Disposition", 'attachment; filename="combined_analysis.pdf"')
                    message.attach(attach)

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, user_email, message.as_string())
                server.quit()

                result += " Combined PDF sent to user."
            msg = "email sent"
            return jsonify({'message': msg})

        else:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            logging.info(f"{timestamp} - User with ID {user_id} made a request. User not found in the database.")
            result = "User ID not found in the database"
            return jsonify({"message":result}) # Return a 404 error response

    else:
        return make_response("User ID not provided in the request", 400)  # Return a 400 error response
