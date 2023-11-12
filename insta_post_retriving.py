import os
import instaloader
import pymongo
import schedule
import time
from datetime import datetime, timedelta
from decouple import config  

MONGO_USERNAME = config('MONGO_USERNAME') 
MONGO_PASSWORD = config('MONGO_PASSWORD')
MONGO_URI = config('MONGO_URI')
MONGO_DB = config('MONGO_DB')
INSTAGRAM_USERNAME = config('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = config('INSTAGRAM_PASSWORD')

L = instaloader.Instaloader()
# L.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)

# Define a function to run the scraping and updating process
def scrape_and_update():
    print("a")
    client = pymongo.MongoClient(f'mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_URI}/')
    # client = pymongo.MongoClient('mongodb://localhost:27017/')
    db_name = MONGO_DB
    db = client.get_database(db_name)
    instagram_creators = db['instagram_creators']
    instagram_posts = db['instagram_posts']
    print("b")
    all_usernames = instagram_creators.find({}, {'username': 1})
    print("c")
    for username_record in all_usernames:
        print(1)
        username = username_record['username']
        print(username)
        profile = instaloader.Profile.from_username(L.context, username)
        try:
            print("a")
            latest_post = instagram_creators.find_one({"username":username})
            print(latest_post)
            if latest_post['lastPublishedAt'] is  None:
                latest_post = None
        except:
            print("b")
            latest_post = None

        if latest_post is not None:
            print("c")
            last_timestamp = latest_post['lastPublishedAt']
            last_timestamp = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            print("d")
            last_timestamp = datetime.now().replace(microsecond=0) - timedelta(days=30)

        print(2)
        post_list = []
        
        for index, post in enumerate(profile.get_posts()):
            print("&")
            print(post.date_utc)
            print(last_timestamp)
            print(type(post.date_utc))
            print(type(last_timestamp))
            if post.date_utc > last_timestamp:
                print("*")
                post_list.append(post)
            else:
                break

        if post_list:
            print(3)
            document_to_insert = []
            for post in post_list:
                print("*")
                post_date_str = post.date_utc.strftime("%Y-%m-%d %H:%M:%S")
                # check if post is already in the database
                if instagram_posts.find_one({"shortcode": post.shortcode}):
                    continue
                else:
                    print("+")
                    document_to_insert.append({"username": username, "shortcode": post.shortcode, "timestamp": post_date_str})

            if document_to_insert:
                instagram_posts.insert_many(document_to_insert)
            instagram_creators.update_one({'username': username}, {'$set': {'lastPublishedAt': post_list[0].date_utc.strftime("%Y-%m-%d %H:%M:%S")}})




def scrape_data(username):
        client = pymongo.MongoClient(f'mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_URI}/')
        # client = pymongo.MongoClient('mongodb://localhost:27017/')
        db_name = MONGO_DB
        db = client.get_database(db_name)

        instagram_creators = db['instagram_creators']
        instagram_posts = db['instagram_posts']

        print(1)
        print(username)
        profile = instaloader.Profile.from_username(L.context, username)
        try:
            print("a")
            latest_post = instagram_creators.find_one({"username":username}, sort=[('publishedAt', pymongo.DESCENDING)])
            print(latest_post)
            if latest_post['timestamp'] is  None:
                latest_post = None
        except:
            print("b")
            latest_post = None

        if latest_post is not None:
            print("c")
            last_timestamp = latest_post['timestamp']
            last_timestamp = datetime.strptime(last_timestamp, "%Y-%m-%d %H:%M:%S")
        else:
            print("d")
            last_timestamp = datetime.now().replace(microsecond=0) - timedelta(days=30)

        print(2)
        post_list = []
        
        for index, post in enumerate(profile.get_posts()):
            print("&")
            print(post.date_utc)
            print(last_timestamp)
            print(type(post.date_utc))
            print(type(last_timestamp))
            if post.date_utc > last_timestamp:
                print("*")
                post_list.append(post)
            else:
                break

        if post_list:
            print(3)
            document_to_insert = []
            for post in post_list:
                print("*")
                post_date_str = post.date_utc.strftime("%Y-%m-%d %H:%M:%S")
                # check if post is already in the database
                if instagram_posts.find_one({"shortcode": post.shortcode}):
                    continue
                else:
                    print("+")
                    document_to_insert.append({"username": username, "shortcode": post.shortcode, "timestamp": post_date_str})

            if document_to_insert:
                instagram_posts.insert_many(document_to_insert)

            instagram_creators.update_one({'username': username}, {'$set': {'timestamp': post_list[0].date_utc.strftime("%Y-%m-%d %H:%M:%S")}})


if __name__ == '__main__':
    #set up scheduler
    # scheduler = schedule.Scheduler()
    # scheduler.every(2).minutes.do(scrape_and_update)
    # while True:
    #     scheduler.run_pending()
    #     time.sleep(1)
    scrape_and_update()