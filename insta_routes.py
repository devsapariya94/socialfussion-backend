from flask import Flask, Blueprint, jsonify
import instaloader
import json
instroute  = Blueprint('instroute', __name__)


@instroute.route('/instagram/post/<username>')
def get_instagram_posts(username):
    loader = instaloader.Instaloader()
    profile = instaloader.Profile.from_username(loader.context, username)

    post_list = []
    for index, post in enumerate(profile.get_posts()):
        if index >= 10:
            break
        post_list.append(post.shortcode)
    print(post_list)
    return jsonify(post_list)