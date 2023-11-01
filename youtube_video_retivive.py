from googleapiclient.discovery import build
import os
from decouple import config  
from datetime import datetime, timedelta
import pymongo

MONGO_USERNAME = config('MONGO_USERNAME')
MONGO_PASSWORD = config('MONGO_PASSWORD')
MONGO_URI = config('MONGO_URI')
MONGO_DB = config('MONGO_DB')
YOUTUBE_API_KEY = config('YOUTUBE_API_KEY')

# Define a function to run the scraping and updating process
def get_yt_videos():
    client = pymongo.MongoClient(f'mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_URI}/')
    # client = pymongo.MongoClient('mongodb://localhost:27017/')
    db_name = MONGO_DB
    db = client.get_database(db_name)

    youtube_videos = db['youtube_videos']
    youtube_following = db['youtube_following']

    get_all_youtuber_channel = youtube_following.find({}, {'channel_id': 1})

    print(1)
    for channel in get_all_youtuber_channel:
        try:
            print(2)
            latest_video = youtube_following.find_one({'channel_id': channel['channel_id']}, sort=[('publishedAt', pymongo.DESCENDING)])

            # publishedat is not there
            if latest_video['publishedAt'] is None:
                latest_video = None

        except:
            print(3)
            latest_video = None
        if latest_video is not None:
            print(4)
            last_timestamp = datetime.strptime(latest_video['publishedAt'], "%Y-%m-%d %H:%M:%S")
        else:
            print(5)
            last_timestamp = datetime.now().replace(microsecond=0) - timedelta(days=10)

        # temp_time = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
        temp_time=last_timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            part='snippet',
            channelId=channel['channel_id'],
            maxResults=50,
            publishedAfter=temp_time
        )
        response = request.execute()

        videos = []
        for item in response['items']:
            print("*")
            if item['id']['kind'] == 'youtube#video':
                print("a")
                video_id = item['id']['videoId']
                video_published_at = item['snippet']['publishedAt']
                videos.append({'videoId': video_id, 'publishedAt': video_published_at})

        if videos:
            print(6)
            for video in videos:
                print("+")
                # check if video is already in the database
                dt = datetime.strptime(video['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
                if youtube_videos.find_one({'video_id': video['videoId']}):
                    continue
                else:
                    print("b")
                    youtube_videos.insert_one({'channel_id': channel['channel_id'], 'video_id': video['videoId'], "timestamp": timestamp})
            dt = datetime.strptime(videos[0]['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
            timestamp = datetime.strftime(dt, "%Y-%m-%d %H:%M:%S")
            youtube_following.update_one({'channel_id': channel['channel_id']}, {'$set': {'publishedAt': timestamp}})
        else:
            continue


if __name__ == '__main__':
    get_yt_videos()
    #set up scheduler
    # schedule.every(1).minutes.do(get_yt_videos)
    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)