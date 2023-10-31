from flask import Flask, Blueprint, jsonify
import requests
from googleapiclient.discovery import build
import dotenv

ytroute  = Blueprint('ytroute', __name__)
API_KEY = dotemv.get('YOUTUBE_API_KEY')
@ytroute.route('/youtube/videos/<channel_id>')
def get_youtube_videos(channel_id):
    endpoint = 'https://www.googleapis.com/youtube/v3/search'
    params = {
        'key': API_KEY,
        'channelId': channel_id,
        'order': 'date', 
        'maxResults': 15, 
        'type': 'video', 
        'part': 'snippet',  
    }

    response = requests.get(endpoint, params=params)
    data = response.json()

    video_ids = []
    if response.status_code == 200:
        # Extract and print video information
        for item in data['items']:
            video_ids.append(item['id']['videoId'])
        return jsonify(video_ids)
    else:
        # Handle API request errors
        error_message = data.get('error', {}).get('message', 'Unknown error')
        return jsonify({'error': error_message}), response.status_code


@ytroute.route('/youtube/get_channel_id/<channel_name>')
def get_channel_id(channel_name):
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    search_response = youtube.search().list(
        q=channel_name,
        type='channel',
        part='id'
    ).execute()

    for search_result in search_response.get('items', []):
        if search_result['id']['kind'] == 'youtube#channel':           
            return jsonify(search_result['id']['channelId'])

    return jsonify('No channel found')

    





