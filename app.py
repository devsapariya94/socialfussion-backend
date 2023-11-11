from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager
from bson import ObjectId

from insta_routes import instroute
from yt_routes import ytroute
from auth import authRoute
from protected_route import protectedRoute
app = Flask(__name__)
login_manager = LoginManager(app)
login_manager.login_view = 'authRoute.login'
CORS(app, origins="*")
app.register_blueprint(instroute)
app.register_blueprint(ytroute)
app.register_blueprint(authRoute)
app.register_blueprint(protectedRoute)
# app.run(debug=True)