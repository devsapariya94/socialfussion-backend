secret = "94532b2dc1c0000892d8f172db569fcb"

import requests
from datetime import datetime, timedelta

# Replace 'YOUR_ACCESS_TOKEN' with the actual access token
access_token = '1038894370766374'+'|'+secret

# Get the current date and the date 10 days ago
end_date = datetime.now().strftime('%Y-%m-%d')
start_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

# Make API request to get all posts from the account
url = f'https://graph.instagram.com/v12.0/me/media?fields=id,caption,media_type,shortcode,timestamp&access_token={access_token}'
response = requests.get(url)

print(response.status_code)
print(response)
data = response.json()

# Filter posts within the last 10 days
recent_posts = [post for post in data.get('data', []) if start_date <= post.get('timestamp')[:10] <= end_date]

# Print shortcodes of filtered posts
for post in recent_posts:
    print(f"Post Shortcode: {post.get('shortcode')}")
