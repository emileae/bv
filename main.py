#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import webapp2
import jinja2
import logging
import os
from string import letters
import json
from datetime import datetime, timedelta
import datetime
import time
import urllib
import re

from google.appengine.ext import ndb
from google.appengine.api import images
from google.appengine.api import memcache
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.datastore.datastore_query import Cursor

from google.appengine.api import taskqueue

#from google.appengine.api import app_identity

#to tell if admin user is logged in
from google.appengine.api import users

#remove @mention links from comments that appear as preview comments under goals
from bs4 import BeautifulSoup

import model
import utils

# cloud storage for new images via app
import cloudstorage as gcs

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

cookie_name = "com.bucketvision"
victory_points = 5
goal_points = 1
share_points = 1
load_goal_num = 12

curator_email = "bucketvision1@gmail.com"

class MainHandler(webapp2.RequestHandler):

#TEMPLATE FUNCTIONS
    def write(self, *a, **kw):
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Content-Type'] = 'text/html'
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    #JSON rendering
    def render_json(self, obj):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        self.response.out.write(json.dumps(obj))

    #COOKIE FUNCTIONS
    # sets a cookie in the header with name, val , Set-Cookie and the Path---not blog
    def set_secure_cookie(self, name, val):
        cookie_val = utils.make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s; Path=/' % (name, cookie_val))# consider imcluding an expire time in cookie(now it closes with browser), see docs
    # reads the cookie from the request and then checks to see if its true/secure(fits our hmac)
    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        if cookie_val:
            cookie_val = urllib.unquote(cookie_val)
        return cookie_val and utils.check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie(cookie_name, str(user.key.id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', '%s=; Path=/' % cookie_name)

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)

        #check format
        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'

        uid = self.read_secure_cookie(cookie_name)

        self.user = uid and model.User.by_id(int(uid))

class Register(MainHandler):
    def get(self):
        user_obj = self.user
        if user_obj:
            self.redirect("/")
        else:
            self.render("register.html", user_obj=user_obj)
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')
        verify_password = self.request.get('verify_password')
        key = self.request.get('key')

        company_name = self.request.get("company_name")
        company_website = self.request.get("company_website")
        facebook_url = self.request.get("facebook_url")
        twitter_url = self.request.get("twitter_url")
        company_type = self.request.get("company_type")
        country = self.request.get("country")
        city = self.request.get("city")
        street_address = self.request.get("street_address")
        position = self.request.get("position")

        error = False
        error_name = ""
        error_password = ""
        error_email = ""
        error_verify = ""
        error_unique = ""

        unique_email = model.User.query( model.User.email == email ).get()
        if unique_email:
            error_unique = "There is already a user registered with that email address"
            error = True

        if not utils.valid_password(password):
            error_password="Your password needs to be between 3 and 20 characters long"
            error = True

        if not utils.valid_email(email):
            error_email="Please type in a valid email address"
            error = True

        if password != verify_password:
            error_verify="Please ensure your passwords match"
            error = True

        if not error:
            temporary_name = email.split("@")[0]
            pw_hash = utils.make_pw_hash(email, password)
            user = model.User(parent=model.users_key(), email=email, pw_hash=pw_hash, name=temporary_name)
            user.put()

            utils.send_mail(email)

            utils.add_count("user")

            self.login(user)
            self.redirect('/')

        else:
            errors = "error_verify="+error_verify+"&error_email="+error_email+"&error_password="+error_password+"&error_unique="+error_unique

            self.redirect("/register?%s" % errors)



class Login(MainHandler):
    def get(self):
        user_obj = self.user
        error = self.request.get("error")
        error_verify = self.request.get("error_verify")
        error_email = self.request.get("error_email")
        error_password = self.request.get("error_password")
        error_unique = self.request.get("error_unique")
        if error_verify or error_email or error_password or error_unique:
            errors = {
                "error_verify": error_verify,
                "error_email": error_email,
                "error_password": error_password,
                "error_unique": error_unique
            }
        else:
            errors = False

        self.render("login.html", user_obj=user_obj, error=error, errors=errors)
    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')

        s = model.User.login(email, password)
        if s:
            self.login(s)
            self.redirect('/feed')
        else:
            self.redirect('/login?error=%s' % "Invalid Email / Password")

class Logout(MainHandler):
    def get(self):
        self.logout()
        self.redirect('/')


class BlobUploadUrl(MainHandler):
    def get(self):
        user_obj = self.user
        #logging.error("!!!!!!!!!!!!!!!!!!!!! made it to backend !!!!!!!!!!!!!!")
        callback_url = self.request.get("callback_url")
        img_type = self.request.get("img_type")

        max_size = 1000000

        if img_type == "goal" or img_type == "vic_pic":
            max_size = 3000000
        elif img_type == "profile":
            max_size = 600000

        if user_obj:
            upload_url = utils.request_blob_url(self, callback_url, max_size)

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            obj = {
            'upload_url': upload_url
            }
            self.response.out.write(json.dumps(obj))



class SaveVideo(MainHandler):
    def post(self):
        video_host = self.request.get("video_host")
        video_url = self.request.get("video_url")
        video_on_profile = self.request.get("video_on_profile")
        company_id = self.request.get("company_id")

        user_obj = self.user
        if user_obj:
            company = model.Company.get_by_id(int(company_id))
            company.video_host = video_host
            company.video_url = video_url
            company.video_on_profile = video_on_profile
            company.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'message': 'saved'
            }
            self.response.out.write(json.dumps(obj))
            #self.redirect("/admin?manage_tab=company")

        else:
            self.redirect("/")





# ===================================================================================================================================================
# ===================================================================================================================================================

class HomePage(MainHandler):
    def get(self):
        user_obj = self.user

        admin_user = users.get_current_user()
        is_admin_user = False

        if admin_user:
            nickname = admin_user.nickname()
            if users.is_current_user_admin():
                is_admin_user = True

        if user_obj:
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(-model.Goal.created, model.Goal.key).fetch_page(load_goal_num, start_cursor=curs)
            #goals, next_curs, more = model.Goal.query().order(-model.Goal.created, model.Goal.key).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

            explore_selected = True
            self.render("base_temp.html", user_obj=user_obj, goals=goals, explore_selected=explore_selected, next=next, is_admin_user=is_admin_user)
        else:
            self.render("login_temp.html")

class CountryExplorer(MainHandler):
    def get(self):

        user_obj = self.user

        admin_user = users.get_current_user()
        is_admin_user = False

        if admin_user:
            nickname = admin_user.nickname()
            if users.is_current_user_admin():
                is_admin_user = True

        countries = model.Country.query().fetch()

        countryCode = self.request.get("countryCode")
        if countryCode and len(countryCode) == 2:
            country = utils.get_country(countryCode)
            logging.error("curated")
            logging.error(countryCode)
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.curated==True, model.Goal.country_key==country.key).order(-model.Goal.likes).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False
        else:
            logging.error("not curated")
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.curated==True).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

        self.render("base_temp.html", user_obj=user_obj, goals=goals, country_explorer_selected=True, next=next, is_admin_user=is_admin_user, countries=countries)


class HowItWorks(MainHandler):
    def get(self):
        user_obj = self.user
        self.render('how_it_works.html', user_obj=user_obj)

class PageGoals(MainHandler):
    def get(self):
        user_obj = self.user

        admin_user = users.get_current_user()
        is_admin_user = False

        if admin_user:
            nickname = admin_user.nickname()
            if users.is_current_user_admin():
                is_admin_user = True

        if user_obj:
            victory = self.request.get("victory")
            goal = self.request.get("goal")
            for_user = self.request.get("for_user")

            curs = Cursor(urlsafe=self.request.get('cursor'))
            if for_user != "no":
                user_profile = model.User.get_by_id(int(for_user), parent = model.users_key())
                if goal == "yes":
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == False, model.Goal.user == user_profile.key).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)
                elif victory == "yes":
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == True, model.Goal.user == user_profile.key).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)
                else:
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == False, model.Goal.user == user_profile.key).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)
            else:
                if goal == "yes":
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(-model.Goal.created, model.Goal.key).fetch_page(load_goal_num, start_cursor=curs)
                elif victory == "yes":
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == True).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)
                else:
                    goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)
                #goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(model.Goal.key).order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

            self.render("ajax_goals.html", goals=goals, next=next, user_obj=user_obj, is_admin_user=is_admin_user)

class PageFeed(MainHandler):
    def get(self):
        user_obj = self.user
        if user_obj:
            following = model.Follow.query( model.Follow.following == user_obj.key ).fetch()#user can follow more than 1000 people but it won't be detected
            following_list = []
            for f in following:
                following_list.append(f.followed)

            if following_list:
                curs = Cursor(urlsafe=self.request.get('cursor'))
                goals, next_curs, more = model.Goal.query(model.Goal.user.IN(following_list)).order(-model.Goal.created).order(model.Goal._key).fetch_page(load_goal_num, start_cursor=curs)
                if more and next_curs:
                    next = next_curs.urlsafe()
                else:
                    next = False

            else:
                goals = []
                next = False
            self.render("feed_ajax.html", user_obj=user_obj, goals=goals, next=next)
        else:
            self.redirect("/login")

class Settings(MainHandler):
    def get(self):
        user_obj = self.user
        if user_obj:
            self.render('settings.html', user_obj=user_obj)

    def post(self):
        user_obj = self.user
        if user_obj:
            user_name = self.request.get("user_name")
            user_description = self.request.get("user_description")
            user_obj.name = user_name
            user_obj.description = user_description
            user_obj.put()

class Visions(MainHandler):
    def get(self):
        user_obj = self.user
        if user_obj:
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved == False, model.Goal.user == user_obj.key).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

            self.render("visions.html", user_obj=user_obj, goals=goals, vision_selected=True, next=next)
        else:
            self.redirect('/login')

class Victories(MainHandler):
    def get(self):
        user_obj = self.user
        if user_obj:
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved == True, model.Goal.user == user_obj.key).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

            self.render("victories.html", user_obj=user_obj, goals=goals, victory_selected=True, next=next)
        else:
            self.redirect("/login")

class Goals(MainHandler):
    def get(self):
        user_obj = self.user

        curs = Cursor(urlsafe=self.request.get('cursor'))
        goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).fetch_page(load_goal_num, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        self.render("goals.html", user_obj=user_obj, goals=goals, goal_selected=True, next=next)

class AddGoal(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:

            goal_img_url = self.request.get("goal_img_url")
            goal_title = self.request.get("goal_title")
            goal_description = self.request.get("goal_description")

            already_achieved = self.request.get("already_achieved")

            goal = utils.add_goal(user_obj, goal_img_url, goal_title, goal_description)
            if already_achieved == "yes":
                if user_obj.key == goal.user:
                    goal.achieved = True
                    goal.put()
                    user_obj.total_victories += 1
                    user_obj.total_points += victory_points
                    utils.set_status(user_obj)
                    user_obj.put()
                self.redirect('/victories')
            else:
                self.redirect("/goals")

class AddGoalAjax(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:

            goal_img_url = None
            goal_title = self.request.get("goal_title")
            goal_description = self.request.get("goal_description")

            already_achieved = self.request.get("already_achieved")

            goal = utils.add_goal(user_obj, goal_img_url, goal_title, goal_description)
            goal_id = goal.key.id()

            if already_achieved == "yes":
                if user_obj.key == goal.user:
                    goal.achieved = True
                    goal.put()
                    user_obj.total_victories += 1
                    user_obj.total_points += victory_points
                    utils.set_status(user_obj)
                    user_obj.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'goal_id': goal_id
            }
            self.response.out.write(json.dumps(obj))

class AddView(MainHandler):
    def post(self, goal_id):
        user_obj = self.user
        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            if goal.user != user_obj.key:
                goal.views += 1;
                goal.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'views': goal.views
            }
            self.response.out.write(json.dumps(obj))

class AddLike(MainHandler):
    def post(self, goal_id):
        user_obj = self.user
        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            liked = model.Like.query( model.Like.user == user_obj.key, model.Like.goal == goal.key ).get()
            if not liked and goal.user != user_obj.key:
                goal.likes += 1;
                goal.put()

                like = model.Like( user = user_obj.key, goal = goal.key )
                like.put()


        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'likes': goal.likes
        }
        self.response.out.write(json.dumps(obj))

class AddVictory(MainHandler):
    def post(self, goal_id):
        user_obj = self.user
        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            if user_obj.key == goal.user:
                goal.achieved = True
                goal.put()
                user_obj.total_victories += 1
                user_obj.total_points += victory_points
                utils.set_status(user_obj)
                user_obj.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'victories': user_obj.total_victories,
                'goal_id': goal.key.id()
            }
            self.response.out.write(json.dumps(obj))

class AddBoard(MainHandler):
    def post(self):

        user_obj = self.user

        if user_obj:
            board_type = self.request.get("board_type")
            board_name = self.request.get("board_name")
            board_description = self.request.get("board_description")

            utils.add_board(user_obj, board_type, board_name, board_description)

class Feed(MainHandler):
    def get(self):
        user_obj = self.user

        if user_obj:
            following = model.Follow.query( model.Follow.following == user_obj.key ).fetch()#user can follow more than 1000 people but it won't be detected
            following_list = []
            for f in following:
                following_list.append(f.followed)

            if following_list:
                following_list.append(self.user.key)
                curs = Cursor(urlsafe=self.request.get('cursor'))
                goals, next_curs, more = model.Goal.query(model.Goal.user.IN(following_list)).order(-model.Goal.created).order(model.Goal._key).fetch_page(load_goal_num, start_cursor=curs)

                if more and next_curs:
                    next = next_curs.urlsafe()
                else:
                    next = False

            else:
                goals = []
                next = False
            self.render("feed.html", user_obj=user_obj, goals=goals, feed_selected=True, next=next)
        else:
            self.redirect("/login")

class GetUserProfile(MainHandler):
    def get(self, user_id):
        user_obj = self.user
        if user_obj:
            user_profile = model.User.get_by_id(int(user_id), parent = model.users_key())
            following = model.Follow.query( model.Follow.following == user_obj.key, model.Follow.followed == user_profile.key ).get()

        else:
            user_profile = model.User.get_by_id(int(user_id), parent = model.users_key())
            following = False

        already_following = False
        if following:
            already_following = True

        last_goal = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == False).order(-model.Goal.created).get()
        last_victory = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == True).order(-model.Goal.created).get()

        last_3_goals = []
        if not last_goal and not last_victory:
            last_3_goals = model.Goal.query(model.Goal.user == user_profile.key).order(-model.Goal.created).fetch(3)
        else:
            last_3_goals = False

        self.render("user_profile_html.html", user_profile=user_profile, already_following=already_following, last_3_goals=last_3_goals, last_goal=last_goal, last_victory=last_victory, user_obj=user_obj)

class GetGoalProfile(MainHandler):
    def get(self, goal_id):
        user_obj = self.user
        if user_obj:
            goal_profile = model.Goal.get_by_id(int(goal_id))
            following = model.Follow.query( model.Follow.following == user_obj.key, model.Follow.followed == goal_profile.user ).get()
        else:
            goal_profile = model.Goal.get_by_id(int(goal_id))
            following = False

        already_following = False
        goal_user = goal_profile.user.get()
        if following:
            already_following = True

        if goal_profile.achieved:
            vic_media = []
            vic_pics = goal_profile.vic_pics
            vic_vids = goal_profile.vic_vids
            for vp in vic_pics:
                vic_media_elem = {}
                vic_media_elem["url"] = vp
                vic_media_elem["type"] = 'pic'
                vic_media.append(vic_media_elem)
            for vv in vic_vids:
                vic_media_elem = {}
                vic_media_elem["url"] = vv
                vic_media_elem["type"] = 'vid'
                vic_media.append(vic_media_elem)
        else:
            vic_media = False

        self.render("goal_profile_html.html", user_obj=user_obj, goal_profile=goal_profile, already_following=already_following, vic_media=vic_media, goal_user=goal_user)

class Follow(MainHandler):
    def post(self, user_id):
        user_obj = self.user
        if user_obj:
            followed_user = model.User.get_by_id(int(user_id), parent = model.users_key())
            user_key = followed_user.key
            following = model.Follow.query( model.Follow.followed == user_key, model.Follow.following == user_obj.key ).get()
            if not following:
                logging.error("user-followed: %s" %user_key)
                logging.error("user-following: %s" %user_obj.key)
                f = model.Follow( following = user_obj.key, followed = user_key )
                f.put()

                followed_user.total_followers += 1
                followed_user.put()

                if user_obj.total_following:
                    user_obj.total_following += 1
                    user_obj.put()
                else:
                    user_obj.total_following = 1
                    user_obj.put()

                self.response.headers['Content-Type'] = 'application/json'
                self.response.headers['Host'] = 'localhost'
                self.response.headers['Access-Control-Allow-Origin'] = '*'
                obj = {
                    'following': 'yes'
                }
                self.response.out.write(json.dumps(obj))

class UnFollow(MainHandler):
    def post(self, user_id):
        user_obj = self.user
        if user_obj:
            followed_user = model.User.get_by_id(int(user_id), parent = model.users_key())
            user_key = followed_user.key
            following = model.Follow.query( model.Follow.followed == user_key, model.Follow.following == user_obj.key ).get()
            if following:
                following.key.delete()

                followed_user.total_followers -= 1
                followed_user.put()

                self.response.headers['Content-Type'] = 'application/json'
                self.response.headers['Host'] = 'localhost'
                self.response.headers['Access-Control-Allow-Origin'] = '*'
                obj = {
                    'following': 'no'
                }
                self.response.out.write(json.dumps(obj))

class UploadProfileImage(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, user_id):
        upload_files = self.get_uploads('user_profile_img')

        blob_info = upload_files[0]
        blob_key = blob_info.key()

        user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())

        # Clean up images
        if user_obj:
            img_obj = model.Image.query( model.Image.user == user_obj.key, model.Image.img_type == "profile" ).get()
            if img_obj:
                images.delete_serving_url(img_obj.blob_key)#delete serving url
                blb = blobstore.BlobInfo.get(img_obj.blob_key)#delete blob info which deletes blob
                if blb:
                    blb.delete()#delete blob info which deletes blob
                img_obj.key.delete()

        img_type = "profile"
        img_url = utils.save_blob_to_image_obj(blob_key, user_obj, img_type)

        if img_url:
            user_obj.profile_img = img_url
            user_obj.put()
            self.redirect('/settings')
        else:
            self.redirect('/settings?error=error')

class UploadGoalImage(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, user_id, goal_id, victory):
        upload_files = self.get_uploads('goal_img')

        blob_info = upload_files[0]
        blob_key = blob_info.key()

        user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())

        goal = model.Goal.get_by_id(int(goal_id))

        img_type = "goal"
        img_url = utils.save_blob_to_goal_image_obj(blob_key, user_obj, img_type, goal)

        if img_url:

            goal.image = img_url
            goal.put()
            if victory == "yes":
                self.redirect('/victories')
            else:
                self.redirect('/goals')
        else:
            self.redirect('/settings?error=error')

class UploadVictoryImage(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, user_id, goal_id):
        upload_files = self.get_uploads('vic_img')

        blob_info = upload_files[0]
        blob_key = blob_info.key()

        user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())

        img_type = "vic_pic"
        img_url = utils.save_blob_to_image_obj(blob_key, user_obj, img_type)

        if img_url:

            goal = model.Goal.get_by_id(int(goal_id))
            goal.vic_pics.append(img_url)
            goal.put()

            self.redirect('/add_victory_media/%s' % goal_id)
        else:
            self.redirect('/add_victory_media/%s?error=error' % goal_id)

class UploadVicImage(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            img_url = self.request.get("vic_img_url")
            goal_id = self.request.get("vic_img_url_goal_id")

            goal = model.Goal.get_by_id(int(goal_id))
            goal.vic_pics.append(img_url)
            goal.put()

            self.redirect('/add_victory_media/%s' % goal_id)
        else:
            self.redirect('/login')

class AddVicVid(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            goal_video_embed = self.request.get("goal_video_embed")
            goal_id = self.request.get("vid_goal_id")

            parsed_vid = utils.youtube_vimeo(goal_video_embed)
            youtube_query = parsed_vid["youtube_query"]

            goal = model.Goal.get_by_id(int(goal_id))
            goal.vic_vids.append(youtube_query)
            goal.put()

            self.redirect('/add_victory_media/%s' % goal_id)
        else:
            self.redirect('/login')

class VictoryMedia(MainHandler):
    def get(self, goal_id):
        user_obj = self.user
        goal = model.Goal.get_by_id(int(goal_id))

        if user_obj and goal:
            if goal.user == user_obj.key:
                vic_media = []
                vic_pics = goal.vic_pics
                vic_vids = goal.vic_vids
                for vp in vic_pics:
                    vic_media_elem = {}
                    vic_media_elem["url"] = vp
                    vic_media_elem["type"] = 'pic'
                    vic_media.append(vic_media_elem)
                for vv in vic_vids:
                    vic_media_elem = {}
                    vic_media_elem["url"] = vv
                    vic_media_elem["type"] = 'vid'
                    vic_media.append(vic_media_elem)
                self.render("victory_media.html", user_obj=user_obj, goal=goal, vic_media=vic_media)
            else:
                self.redirect("/victories")

class EditGoal(MainHandler):
    def get(self, goal_id):
        user_obj = self.user
        goal = model.Goal.get_by_id(int(goal_id))
        goal_user = goal.user.get()

        if goal and user_obj:
            self.render("edit_goal.html", user_obj=user_obj, goal=goal, goal_user=goal_user)
        else:
            self.redirect('/login')

class ImgPos(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            top = self.request.get("top")
            goal_id = self.request.get("goal_id")

            goal = model.Goal.get_by_id(int(goal_id))
            goal.img_top = top
            goal.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'top': top
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class EditTitleDescription(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            edit_url = self.request.get("edit_url")
            edit_title = self.request.get("edit_title")
            edit_description = self.request.get("edit_description")
            goal_id = self.request.get("goal_id")

            goal = model.Goal.get_by_id(int(goal_id))

            old_img_url = goal.image

            image_stored = model.Image.query( model.Image.serving_url == old_img_url ).get()
            if image_stored:
                images.delete_serving_url(image_stored.blob_key)#delete serving url
                blb = blobstore.BlobInfo.get(image_stored.blob_key)#delete blob info which deletes blob
                if blb:
                    blb.delete()#delete blob info which deletes blob
                image_stored.key.delete()

            goal.image = edit_url
            goal.img_top = "0px"
            goal.title = edit_title
            goal.description = edit_description
            goal.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'title': edit_title,
                'description': edit_description,
                'edit_url': edit_url,
                'goal_id': goal_id
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class MakeCover(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            img_url = self.request.get("img_url")
            goal_id = self.request.get("goal_id")
            goal = model.Goal.get_by_id(int(goal_id))

            if goal.achieved:
                victory_images = goal.vic_pics
                victory_images.remove(img_url)
                victory_images.append(goal.image)
                old_cover = goal.image
                goal.image = img_url
                goal.put()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'img_url': img_url,
                'old_cover': old_cover
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class DeleteMedia(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            img_url = self.request.get("img_url")
            goal_id = self.request.get("goal_id")
            goal = model.Goal.get_by_id(int(goal_id))

            vic_pics = goal.vic_pics
            if img_url in vic_pics:
                vic_pics.remove(img_url)
            vic_vids = goal.vic_vids
            if img_url in vic_vids:
                vic_vids.remove(img_url)

            goal.vic_pics = vic_pics
            goal.vic_vids = vic_vids

            goal.put()

            uploaded_image = model.Image.query( model.Image.serving_url == img_url ).get()#only for single image
            if uploaded_image:
                images.delete_serving_url(uploaded_image.blob_key)#delete serving url
                blb = blobstore.BlobInfo.get(uploaded_image.blob_key)#delete blob info which deletes blob
                if blb:
                    blb.delete()#delete blob info which deletes blob
                uploaded_image.key.delete()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'message': 'deleted'
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class DeleteGoal(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            goal_id = self.request.get("goal_id")
            goal = model.Goal.get_by_id(int(goal_id))

            uploaded_image = model.Image.query( model.Image.goal == goal.key ).get()#only for single image
            if uploaded_image:
                images.delete_serving_url(uploaded_image.blob_key)#delete serving url
                blb = blobstore.BlobInfo.get(uploaded_image.blob_key)#delete blob info which deletes blob
                if blb:
                    blb.delete()#delete blob info which deletes blob
                uploaded_image.key.delete()

            user_obj.total_goals -= 1;
            user_obj.put()

            goal.key.delete()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'goal_id': goal_id,
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class StealGoal(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            goal_id = self.request.get("steal_goal")

            goal = model.Goal.get_by_id(int(goal_id))

            goal_img_url = goal.image
            goal_title = goal.title
            goal_description = goal.description

            new_goal = utils.add_goal(user_obj, goal_img_url, goal_title, goal_description)

            self.redirect("/")

class StealVictory(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            goal_id = self.request.get("steal_goal")

            goal = model.Goal.get_by_id(int(goal_id))

            goal_img_url = goal.image
            goal_title = goal.title
            goal_description = goal.description

            new_goal = utils.add_victory(user_obj, goal_img_url, goal_title, goal_description)

            self.redirect("/")

class GoalPage(MainHandler):
    def get(self, goal_id):
        user_obj = self.user
        goal = model.Goal.get_by_id(int(goal_id))
        #goals = model.Goal.query().fetch(load_goal_num)
        user = goal.user.get()

        curs = Cursor(urlsafe=self.request.get('cursor'))
        goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(-model.Goal.created, model.Goal.key).fetch_page(load_goal_num, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        explore_selected = False

        if goal.achieved:
            vic_media = []
            vic_pics = goal.vic_pics
            vic_vids = goal.vic_vids
            for vp in vic_pics:
                vic_media_elem = {}
                vic_media_elem["url"] = vp
                vic_media_elem["type"] = 'pic'
                vic_media.append(vic_media_elem)
            for vv in vic_vids:
                vic_media_elem = {}
                vic_media_elem["url"] = vv
                vic_media_elem["type"] = 'vid'
                vic_media.append(vic_media_elem)
        else:
            vic_media = False

        self.render("goal_page.html", g=goal, user=user, user_obj=user_obj, goals=goals, next=next, explore_selected=explore_selected, vic_media=vic_media)

class UploadEditImage(blobstore_handlers.BlobstoreUploadHandler):
    def post(self, user_id, goal_id):
        upload_files = self.get_uploads('goal_img')

        blob_info = upload_files[0]
        blob_key = blob_info.key()

        user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())
        goal = model.Goal.get_by_id(int(goal_id))

        old_img_url = goal.image

        image_stored = model.Image.query( model.Image.serving_url == old_img_url ).get()
        if image_stored:
            images.delete_serving_url(image_stored.blob_key)#delete serving url
            blb = blobstore.BlobInfo.get(image_stored.blob_key)#delete blob info which deletes blob
            if blb:
                blb.delete()#delete blob info which deletes blob
            image_stored.key.delete()

        img_type = "goal"
        img_url = utils.save_blob_to_image_obj(blob_key, user_obj, img_type)

        goal.image = img_url
        goal.img_top = "0px"
        goal.put()

        self.redirect('/edit_goal/%s' % goal_id)

class ForgotPassword(MainHandler):
    def post(self):
        email = self.request.get("recovery_email")

        user_obj = model.User.by_email(email)

        if user_obj:
            message = "your new password has been emailed to %s" % email
            utils.generate_new_password(email)
        else:
            message = "there is no user registered with the email: %s" % email

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class ChangeEmail(MainHandler):
    def post(self):
        password = self.request.get("password")
        old_email = self.request.get("old_email")
        new_email = self.request.get("new_email")

        user_obj = self.user
        if user_obj:
            if user_obj.email == old_email:
                s = model.User.login(old_email, password)
                if s:
                    if not utils.valid_email(new_email):
                        message = "invalid email"
                    else:
                        new_pw_hash = utils.make_pw_hash(new_email, password)
                        user_obj.email = new_email
                        user_obj.pw_hash = new_pw_hash
                        user_obj.put()
                        message = "success"
                else:
                    message = "invalid email password combination"
            else:
                message = "invalid old email"
        else:
            message = "not logged in"

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class ChangePassword(MainHandler):
    def post(self):
        old_password = self.request.get("old_password")
        new_password = self.request.get("new_password")
        repeat_password = self.request.get("repeat_password")

        user_obj = self.user
        if user_obj:
            if new_password == repeat_password:
                s = model.User.login(user_obj.email, old_password)
                if s:
                    if not utils.valid_password(new_password):
                        message = "invalid password"
                    else:
                        new_pw_hash = utils.make_pw_hash(user_obj.email, new_password)
                        user_obj.pw_hash = new_pw_hash
                        user_obj.put()
                        message = "success"
                else:
                    message = "invalid password"
            else:
                message = "new passwords don't match"
        else:
            message = "not logged in"

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class DeleteAccount(MainHandler):
    def post(self):
        user_obj = self.user

        users_images = model.Image.query(model.Image.user == user_obj.key).fetch()
        for i in users_images:
            images.delete_serving_url(i.blob_key)#delete serving url
            blb = blobstore.BlobInfo.get(i.blob_key)#delete blob info which deletes blob
            if blb:
                blb.delete()#delete blob info which deletes blob
            i.key.delete()

        users_following = model.Follow.query(model.Follow.following == user_obj.key).fetch()
        for f in users_following:
            f.key.delete()

        users_followed = model.Follow.query(model.Follow.followed == user_obj.key).fetch()
        for ff in users_followed:
            ff.key.delete()

        users_likes = model.Like.query(model.Like.user == user_obj.key).fetch()
        for l in users_likes:
            l.key.delete()

        user_goals = model.Goal.query(model.Goal.user == user_obj.key).fetch()
        for g in user_goals:
            g.key.delete()

        user_obj.key.delete()

        self.render("delete_user.html")

class SearchUsers(MainHandler):
    def get(self):
        user_email = self.request.get("user_email")
        users = model.User.query(model.User.email == user_email).fetch(10)

        users_list = []
        for u in users:
            users_obj = {}
            users_obj["name"] = u.name
            users_obj["id"] = u.key.id()
            users_list.append(users_obj)

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'users': users_list
        }
        self.response.out.write(json.dumps(obj))

class UserGoals(MainHandler):
    def get(self, user_id):
        user_obj = self.user
        if user_obj:
            user_profile = model.User.get_by_id(int(user_id), parent = model.users_key())

            following = model.Follow.query( model.Follow.following == user_obj.key, model.Follow.followed == user_profile.key ).get()
            already_following = False
            if following:
                already_following = True

            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved == False, model.Goal.user == user_profile.key).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False
            explore_selected = True

            # for the last goal / victory
            last_goal = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == False).order(-model.Goal.created).get()
            last_victory = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == True).order(-model.Goal.created).get()

            last_3_goals = []
            if not last_goal and not last_victory:
                last_3_goals = model.Goal.query(model.Goal.user == user_profile.key).order(-model.Goal.created).fetch(3)
            else:
                last_3_goals = False

            self.render("user_goals.html", user_obj=user_obj, goals=goals, next=next, user_profile=user_profile, already_following=already_following, last_goal=last_goal, last_victory=last_victory, last_3_goals=last_3_goals)
        else:
            self.redirect("/login")

class UserVictories(MainHandler):
    def get(self, user_id):
        user_obj = self.user
        if user_obj:
            user_profile = model.User.get_by_id(int(user_id), parent = model.users_key())

            following = model.Follow.query( model.Follow.following == user_obj.key, model.Follow.followed == user_profile.key ).get()
            already_following = False
            if following:
                already_following = True

            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved == True, model.Goal.user == user_profile.key).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False
            explore_selected = True

            # for the last goal / victory
            last_goal = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == False).order(-model.Goal.created).get()
            last_victory = model.Goal.query(model.Goal.user == user_profile.key, model.Goal.achieved == True).order(-model.Goal.created).get()

            last_3_goals = []
            if not last_goal and not last_victory:
                last_3_goals = model.Goal.query(model.Goal.user == user_profile.key).order(-model.Goal.created).fetch(3)
            else:
                last_3_goals = False

            self.render("user_victories.html", user_obj=user_obj, goals=goals, next=next, user_profile=user_profile, already_following=already_following, last_goal=last_goal, last_victory=last_victory, last_3_goals=last_3_goals)
        else:
            self.redirect("/login")

class SharePoint(MainHandler):
    def post(self):
        user_obj = self.user
        if user_obj:
            user_obj.total_points += share_points
            user_obj.put()
        else:
            self.redirect('/login')

class VictoryAlbum(MainHandler):
    def get(self, goal_id):
        user_obj = self.user
        goal = model.Goal.get_by_id(int(goal_id))

        if goal:
            vic_media = []
            vic_pics = goal.vic_pics
            vic_vids = goal.vic_vids
            for vp in vic_pics:
                vic_media_elem = {}
                vic_media_elem["url"] = vp
                vic_media_elem["type"] = 'pic'
                vic_media.append(vic_media_elem)
            for vv in vic_vids:
                vic_media_elem = {}
                vic_media_elem["url"] = vv
                vic_media_elem["type"] = 'vid'
                vic_media.append(vic_media_elem)
            self.render("victory_album.html", user_obj=user_obj, goal=goal, vic_media=vic_media)
        else:
                self.redirect("/feed")

class PopulateProfile(MainHandler):
    def get(self):
        users = model.User.query().fetch()
        for u in users:
            if not u.profile_img:
                u.profile_img = "/static/images/profile.jpg"
                u.put()

class LeaderBoard(MainHandler):
    def get(self):
        users = model.User.query().order( -model.User.total_points ).fetch(1000)

        total_users = len(users)

        self.render("dashboard.html", users=users, total_users=total_users)

class AdminManageGoals(MainHandler):
    def get(self):
        pass

class APIGoals(MainHandler):
    def get(self):

        num_items = 10

        curs = Cursor(urlsafe=self.request.get('cursor'))
        goals, next_curs, more = model.Goal.query(model.Goal.achieved == False).order(-model.Goal.created).fetch_page(num_items, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        logged_in_user_obj = False
        userid = self.request.get("userid")
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

            user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

            logged_in_user_obj = {
            "has_notifications": user_obj.has_notifications,
            "notification_count": user_obj.notifications,
            "has_comments": user_obj.has_notifications,
            "comment_count": user_obj.notifications,
            "has_mentions": user_obj.has_notifications,
            "mention_count": user_obj.notifications,
            "new_followers": user_obj.has_notifications,
            "new_followers_count": user_obj.notifications,
            }

        fmt = '%Y-%m-%d %H:%M:%S'

        goal_list = []
        for g in goals:
            goal_json = {}
            goal_json["id"] = g.key.id()
            goal_json["image"] = g.image
            goal_json["title"] = g.title
            goal_json["description"] = g.description
            goal_json["likes"] = g.likes
            goal_json["views"] = g.views
            goal_json["achieved"] = g.achieved
            goal_json["vic_pics"] = g.vic_pics
            goal_json["user_name"] = g.user.get().name
            goal_json["has_comments"] = g.has_comments
            goal_json["recent_comment"] = g.recent_comment
            goal_json["comment_count"] = g.comment_count
            goal_json["userid"] = g.user.get().key.id()
            avatar = g.user.get().profile_img
            if avatar =="/static/images/profile.jpg":
                goal_json["avatar"] = utils.base_url+avatar
            else:
                goal_json["avatar"] = avatar

            goal_json["created"] = g.created.strftime(fmt)

            liked = False
            if user_obj:
                liked = model.Like.query(model.Like.user == user_obj.key, model.Like.goal == g.key).get()
            if liked:
                goal_json["liked"] = "yes"
            else:
                goal_json["liked"] = "no"

            goal_list.append(goal_json)

        obj = {
        "next_page": next,
        "goals": goal_list,
        "logged_in_user": logged_in_user_obj
        }

        self.render_json(obj)

class APICountries(MainHandler):
    def get(self):
        countries = model.Country.query().order(model.Country.countryName).fetch(use_cache=False, use_memcache=False)

        country_list = []

        for c in countries:
            country_obj = {}
            country_obj["countryName"] = c.countryName
            country_obj["countryCode"] = c.countryCode
            country_obj["totalGoals"] = c.number_goals
            country_obj["countryId"] = c.key.id()
            country_list.append(country_obj)

        self.render_json({
            "countries": country_list
            })

class APIInspirations(MainHandler):
    def get(self):

        countryCode = self.request.get("countryCode")
        if countryCode and len(countryCode) == 2:
            country = utils.get_country(countryCode)
            logging.error("curated")
            logging.error(countryCode)
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.curated==True, model.Goal.country_key==country.key).order(-model.Goal.likes).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False
        else:
            logging.error("not curated")
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query().order(-model.Goal.created).fetch_page(load_goal_num, start_cursor=curs)

            if more and next_curs:
                next = next_curs.urlsafe()
            else:
                next = False

        fmt = '%Y-%m-%d %H:%M:%S'

        logged_in_user_obj = False
        userid = self.request.get("userid")
        user_obj = False
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

            logged_in_user_obj = {
            "has_notifications": user_obj.has_notifications,
            "notification_count": user_obj.notifications,
            "has_comments": user_obj.has_notifications,
            "comment_count": user_obj.notifications,
            "has_mentions": user_obj.has_notifications,
            "mention_count": user_obj.notifications,
            "new_followers": user_obj.has_notifications,
            "new_followers_count": user_obj.notifications,
            }

        goal_list = []

        for g in goals:
            goal_json = {}
            goal_json["id"] = g.key.id()
            goal_json["image"] = g.image
            goal_json["title"] = g.title
            goal_json["description"] = g.description
            goal_json["likes"] = g.likes
            goal_json["views"] = g.views
            goal_json["achieved"] = g.achieved
            goal_json["vic_pics"] = g.vic_pics
            goal_json["user_name"] = g.user.get().name
            goal_json["has_comments"] = g.has_comments
            goal_json["recent_comment"] = g.recent_comment
            goal_json["comment_count"] = g.comment_count
            goal_json["userid"] = g.user.get().key.id()
            avatar = g.user.get().profile_img
            if avatar =="/static/images/profile.jpg":
                goal_json["avatar"] = utils.base_url+avatar
            else:
                goal_json["avatar"] = avatar

            goal_json["curated"] = g.curated
            goal_json["created"] = g.created.strftime(fmt)

            liked = False
            if user_obj:
                liked = model.Like.query(model.Like.user == user_obj.key, model.Like.goal == g.key).get()
            if liked:
                goal_json["liked"] = "yes"
            else:
                goal_json["liked"] = "no"

            goal_list.append(goal_json)

        logging.error(goal_list)

        obj = {
        "next_page": next,
        "goals": goal_list,
        "logged_in_user": logged_in_user_obj
        }

        self.render_json(obj)

class APINews(MainHandler):
    def get(self):
        userid = self.request.get("userid")
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

            following = model.Follow.query( model.Follow.following == user_obj.key ).fetch()#user can follow more than 1000 people but it won't be detected
            following_list = []
            following_list.append(user_obj.key)
            for f in following:
                following_list.append(f.followed)

            if following_list:
                curs = Cursor(urlsafe=self.request.get('cursor'))
                goals, next_curs, more = model.Goal.query(model.Goal.user.IN(following_list)).order(-model.Goal.created).order(model.Goal._key).fetch_page(load_goal_num, start_cursor=curs)

                if more and next_curs:
                    next = next_curs.urlsafe()
                else:
                    next = False

            else:
                goals = []
                next = False

            fmt = '%Y-%m-%d %H:%M:%S'
            goal_list = []
            logged_in_user_obj = False
            for g in goals:
                goal_json = {}
                goal_json["id"] = g.key.id()
                goal_json["image"] = g.image
                goal_json["title"] = g.title
                goal_json["description"] = g.description
                goal_json["likes"] = g.likes
                goal_json["views"] = g.views
                goal_json["achieved"] = g.achieved
                goal_json["vic_pics"] = g.vic_pics
                goal_json["user_name"] = g.user.get().name
                goal_json["has_comments"] = g.has_comments
                goal_json["recent_comment"] = g.recent_comment
                goal_json["comment_count"] = g.comment_count
                goal_json["userid"] = g.user.get().key.id()
                avatar = g.user.get().profile_img
                if avatar =="/static/images/profile.jpg":
                    goal_json["avatar"] = utils.base_url+avatar
                else:
                    goal_json["avatar"] = avatar

                goal_json["created"] = g.created.strftime(fmt)

                liked = False
                if user_obj:
                    liked = model.Like.query(model.Like.user == user_obj.key, model.Like.goal == g.key).get()
                if liked:
                    goal_json["liked"] = "yes"
                else:
                    goal_json["liked"] = "no"

                goal_list.append(goal_json)

                logged_in_user_obj = {
                "has_notifications": user_obj.has_notifications,
                "notification_count": user_obj.notifications,
                "has_comments": user_obj.has_notifications,
                "comment_count": user_obj.notifications,
                "has_mentions": user_obj.has_notifications,
                "mention_count": user_obj.notifications,
                "new_followers": user_obj.has_notifications,
                "new_followers_count": user_obj.notifications,
                }

            obj = {
            "message": "success",
            "next_page": next,
            "goals": goal_list,
            "logged_in_user": logged_in_user_obj
            }

            self.render_json(obj)

        else:
            self.render_json({
                "message": "fail",
                })

class APIGoal(MainHandler):
    def get(self, goal_id):
        userid = self.request.get("userid")

        user_obj = False
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

        g = model.Goal.get_by_id(int(goal_id))

        comment_list = []
        comments = False
        if g.has_comments:
            comments = model.Comment.query(model.Comment.goal == g.key).order(-model.Comment.created).fetch()

        if comments:
            for c in comments:
                comment_obj = {}
                comment_obj["comment"] = c.comment
                comment_obj["commentor_name"] = c.user.get().name
                comment_obj["commentor_id"] = c.user.get().key.id()
                comment_list.append(comment_obj)

        goal_json = {}
        goal_json["id"] = g.key.id()
        goal_json["achieved"] = g.achieved
        goal_json["vic_pics"] = g.vic_pics
        goal_json["image"] = g.image
        goal_json["title"] = g.title
        goal_json["description"] = g.description
        goal_json["likes"] = g.likes
        goal_json["views"] = g.views
        goal_json["user_name"] = g.user.get().name
        goal_json["has_comments"] = g.has_comments
        goal_json["recent_comment"] = g.recent_comment
        goal_json["comment_count"] = g.comment_count
        goal_json["comments"] = comment_list
        goal_json["userid"] = g.user.get().key.id()
        avatar = g.user.get().profile_img
        if avatar =="/static/images/profile.jpg":
            goal_json["avatar"] = utils.base_url+avatar
        else:
            goal_json["avatar"] = avatar

        fmt = '%Y-%m-%d %H:%M:%S'
        goal_json["created"] = g.created.strftime(fmt)

        liked = False
        if user_obj:
            liked = model.Like.query(model.Like.user == user_obj.key, model.Like.goal == g.key).get()
        if liked:
            goal_json["liked"] = "yes"
        else:
            goal_json["liked"] = "no"

        self.render_json({
            "goal_obj": goal_json
            })

class APIGetGoalGeneral(MainHandler):
    def get(self):
        num_items = self.request.get("num_items")
        goal_type = self.request.get("goal_type")
        user_id = self.request.get("user_id")
        if not user_id:
            user_id = self.request.get("userid")

        #not doing anything with order yet... may need to create a utility function
        order = self.request.get("order")

        if not num_items:
            num_items = 10

        if not goal_type:
            goal_type = 'goal'

        if goal_type == 'goal':
            achieved = False
        else:
            achieved = True

        next_curs = False
        more = False
        goals = False

        user_obj = False

        if not user_id:
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.achieved==achieved).order(-model.Goal.created).fetch_page(num_items, start_cursor=curs)
        else:
            logging.error("USER_ID: %s" % user_id)
            #user_obj = model.User.get_by_id(int(user_id))
            try:
                user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())
            except:
                user_obj = model.User.query(model.User.name == user_id).get()
            logging.error(user_obj)
            #user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())
            #logging.error(user_obj)
            if user_obj:
                curs = Cursor(urlsafe=self.request.get('cursor'))
                goals, next_curs, more = model.Goal.query(model.Goal.achieved==achieved, model.Goal.user==user_obj.key).order(-model.Goal.created).fetch_page(num_items, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        fmt = '%Y-%m-%d %H:%M:%S'

        if goals:
            goal_list = []
            for g in goals:
                goal_json = {}
                goal_json["id"] = g.key.id()
                goal_json["image"] = g.image
                goal_json["title"] = g.title
                goal_json["description"] = g.description
                goal_json["likes"] = g.likes
                goal_json["views"] = g.views
                goal_json["achieved"] = g.achieved
                goal_json["vic_pics"] = g.vic_pics
                goal_json["user_name"] = g.user.get().name
                goal_json["has_comments"] = g.has_comments
                goal_json["recent_comment"] = g.recent_comment
                goal_json["comment_count"] = g.comment_count
                goal_json["userid"] = g.user.get().key.id()
                avatar = g.user.get().profile_img
                if avatar =="/static/images/profile.jpg":
                    goal_json["avatar"] = utils.base_url+avatar
                else:
                    goal_json["avatar"] = avatar

                goal_json["created"] = g.created.strftime(fmt)

                liked = False
                if user_obj:
                    liked = model.Like.query(model.Like.user == user_obj.key, model.Like.goal == g.key).get()
                if liked:
                    goal_json["liked"] = "yes"
                else:
                    goal_json["liked"] = "no"

                goal_list.append(goal_json)


            obj = {
            "next_page": next,
            "goals": goal_list,
            "goal_type": goal_type,
            "num_items": num_items,
            }
        else:
            obj = {
            "next_page": next,
            "goals": goals,
            "goal_type": False,
            "num_items": 0,
            }

        self.render_json(obj)

class APIRegister(MainHandler):
    def options(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

    def post(self):
        name = self.request.get('name')
        email = self.request.get('email')
        password = self.request.get('password')
        verify_password = self.request.get('verify_password')
        key = self.request.get('key')

        error = False
        error_name = ""
        error_password = ""
        error_email = ""
        error_verify = ""
        error_unique = ""
        error_unique_name = ""

        name = re.sub('[^0-9a-zA-Z]+', '', name)

        unique_name = model.User.query( model.User.name == name ).get()
        if unique_name:
            error_unique_name = "There is already a user registered with that name"
            error = True

        unique_email = model.User.query( model.User.email == email ).get()
        if unique_email:
            error_unique = "There is already a user registered with that email address"
            error = True

        if not utils.valid_password(password):
            error_password="Your password needs to be between 3 and 20 characters long"
            error = True

        if not utils.valid_email(email):
            error_email="Please type in a valid email address"
            error = True

        if password != verify_password:
            error_verify="Please ensure your passwords match"
            error = True

        if not error:
            logging.error("NO ERRORS...")
            #temporary_name = email.split("@")[0]
            pw_hash = utils.make_pw_hash(email, password)
            user = model.User(parent=model.users_key(), email=email, pw_hash=pw_hash, name=name)
            user.put()

            utils.add_count("user")

            #utils.send_mail(email)

            self.render_json({"message": 'success', "userid": user.key.id(), "long_message": "register"})

        else:
            errors = [error_verify, error_email, error_password, error_unique, error_unique_name]

            self.render_json({"message": "fail", "errors": errors, "long_message": "register"})



class APILogin(MainHandler):
    def options(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

    def post(self):
        email = self.request.get('email')
        password = self.request.get('password')

        logging.error("EMAIL --- PASSWORD")
        logging.error(email)
        logging.error(password)

        s = model.User.login(email, password)
        if s:
            self.render_json({"message":"success", "userid": s.key.id(), "long_message": "login"})
        else:
            self.render_json({"message":"fail", "errors": ["Invalid Email/Password"], "long_message": "login"})


class APIUser(MainHandler):
    def get(self, user_id):
        loggedin_userid = self.request.get("userid")
        logging.error("loggedin_userid")
        logging.error(loggedin_userid)

        user_obj = False
        if loggedin_userid:
            user_obj = model.User.get_by_id(int(loggedin_userid), parent = model.users_key())

        try:
            user = model.User.get_by_id(int(user_id), parent = model.users_key())
        except:
            user = model.User.query(model.User.name == user_id).get()

        if user and user_obj:
            following = model.Follow.query(model.Follow.followed == user.key, model.Follow.following ==user_obj.key).get()
            is_loggedin_user = True

            logging.error("follow obj 1")
            logging.error(following)

            if following:
                is_following = True
            else:
                is_following = False
        else:
            logging.error("no follow obj")
            is_following = False
            is_loggedin_user = False

        user_json = {}
        if user:
            user_json["name"] = user.name
            user_json["id"] = user.key.id()
            user_json["description"] = user.description
            user_json["email"] = user.email
            user_json["total_points"] = user.total_points
            user_json["status"] = user.status
            user_json["total_goals"] = user.total_goals
            user_json["total_victories"] = user.total_victories
            user_json["total_followers"] = user.total_followers
            user_json["total_following"] = user.total_following
            user_json["profile_img"] = user.profile_img
            user_json["following"] = is_following
            user_json["loggedInUser"] = is_loggedin_user
            user_json["has_comments"] = user.has_comments
            user_json["comment_count"] = user.comment_count
            user_json["notifications"] = user.notifications
            message = "success"
        else:
            user_json = False
            message = "fail"

        self.render_json({
            "message": message,
            "user_obj": user_json
            })
class APIFollowers(MainHandler):
    def get(self, user_id):
        user_obj = model.User.get_by_id(int(user_id), parent=model.users_key())

        curs = Cursor(urlsafe=self.request.get('cursor'))
        follower_objs, next_curs, more = model.Follow.query(model.Follow.followed == user_obj.key).fetch_page(50, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        follower_list = []
        for f in follower_objs:
            follower_obj = {}
            user = f.following.get()
            follower_obj["name"] = user.name
            follower_obj["id"] = user.key.id()
            follower_obj["description"] = user.description
            follower_obj["profile_img"] = user.profile_img
            follower_obj["total_goals"] = user.total_goals
            follower_obj["total_victories"] = user.total_victories
            follower_list.append(follower_obj)

        self.render_json({
            "followers": follower_list,
            "next": next
            })

class APIFollowing(MainHandler):
    def get(self, user_id):
        user_obj = model.User.get_by_id(int(user_id), parent=model.users_key())

        curs = Cursor(urlsafe=self.request.get('cursor'))
        follower_objs, next_curs, more = model.Follow.query(model.Follow.following == user_obj.key).fetch_page(50, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        follower_list = []
        for f in follower_objs:
            follower_obj = {}
            user = f.followed.get()
            follower_obj["name"] = user.name
            follower_obj["id"] = user.key.id()
            follower_obj["description"] = user.description
            follower_obj["profile_img"] = user.profile_img
            follower_obj["total_goals"] = user.total_goals
            follower_obj["total_victories"] = user.total_victories
            follower_list.append(follower_obj)

        self.render_json({
            "following": follower_list,
            "next": next
            })


class APIFollow(MainHandler):
    def post(self, user_id):
        user_obj_id = self.request.get("user_obj_id")
        user_obj = model.User.get_by_id(int(user_obj_id), parent = model.users_key())
        if user_obj:
            followed_user = model.User.get_by_id(int(user_id), parent = model.users_key())
            user_key = followed_user.key
            following = model.Follow.query( model.Follow.followed == user_key, model.Follow.following == user_obj.key ).get()
            if not following:
                logging.error("user-followed: %s" %user_key)
                logging.error("user-following: %s" %user_obj.key)
                f = model.Follow( following = user_obj.key, followed = user_key )
                f.put()

                followed_user.total_followers += 1
                followed_user.put()
                if user_obj.total_following:
                    user_obj.total_following += 1
                    user_obj.put()
                else:
                    user_obj.total_following = 1
                    user_obj.put()

                notified_user = followed_user
                if not notified_user.notifications:
                    notified_user.notifications = 1
                else:
                    notified_user.notifications += 1
                notified_user.has_notifications = False
                notified_user.put()

                message = ' is following you'
                note = model.Notification(follow=True, type="follow", message=message, user=notified_user.key, trigger_user=user_obj.key, trigger_user_name=user_obj.name)
                note.put()

                self.response.headers['Content-Type'] = 'application/json'
                self.response.headers['Host'] = 'localhost'
                self.response.headers['Access-Control-Allow-Origin'] = '*'
                obj = {
                    'following': 'yes'
                }

                self.render_json(obj)
        else:
            self.render_json({
                "message": "fail"
                })

class APIUnFollow(MainHandler):
    def post(self, user_id):
        user_obj_id = self.request.get("user_obj_id")
        user_obj = model.User.get_by_id(int(user_obj_id), parent = model.users_key())
        if user_obj:
            followed_user = model.User.get_by_id(int(user_id), parent = model.users_key())
            user_key = followed_user.key
            following = model.Follow.query( model.Follow.followed == user_key, model.Follow.following == user_obj.key ).get()
            if following:
                following.key.delete()

                followed_user.total_followers -= 1
                followed_user.put()

                if user_obj.total_following > 0:
                    user_obj.total_following -= 1
                    user_obj.put()

                self.response.headers['Content-Type'] = 'application/json'
                self.response.headers['Host'] = 'localhost'
                self.response.headers['Access-Control-Allow-Origin'] = '*'
                obj = {
                    'following': 'no'
                }
                self.render_json(obj)
        else:
            self.render_json({
                "message": "fail"
                })

class APICloudStorage(MainHandler):
    def post(self):
        self.response.headers.add_header("Access-Control-Allow-Origin", '*')

        userid = self.request.get("userid")
        goal_title = self.request.get("title")
        goal_description = self.request.get("description")
        already_achieved = self.request.get("already_achieved")
        victory_album_id = self.request.get("victory_album_id")

        logging.error("victory_album_id")
        logging.error(victory_album_id)

        try:
            goal = model.Goal.get_by_id(int(victory_album_id))
        except:
            victory_album_id = False

        if userid:

            logging.error("PARAMS")
            logging.error(victory_album_id)

            user_obj = model.User.get_by_id(int(userid), parent = model.users_key())

            f = self.request.POST['image']

            #if f:
                # - - -
            serving_url = ''#just assign it adn reassign later

            if not victory_album_id:
                goal = utils.add_goal(user_obj, serving_url, goal_title, goal_description)
            # goal = utils.add_goal(user_obj, serving_url, goal_title, goal_description)

            fname = '/%s.appspot.com/goal_%s.jpg' % ( utils.app_id, goal.key.id())

            gcs_file = gcs.open(fname, 'w', content_type="image/jpeg")
            gcs_file.write(self.request.get('image'))
            gcs_file.close()

            gcs_filename = "/gs%s" % fname
            serving_url = images.get_serving_url(blobstore.create_gs_key(gcs_filename))

            if victory_album_id:
                goal.vic_gcs_filenames.append(gcs_filename)
                goal.vic_pics.append(serving_url)
                goal.put()
                goal_type = "victory"
            else:
                goal.gcs_filename = gcs_filename

                if already_achieved == "yes":
                    goal_type = "victory"
                else:
                    goal_type = "goal"

                if already_achieved == "yes":
                    if user_obj.key == goal.user:
                        goal.achieved = True
                        user_obj.total_victories += 1
                        user_obj.total_points += victory_points
                        utils.set_status(user_obj)
                        user_obj.put()

                #put goal after everything
                goal.image = serving_url
                goal.put()

            # self.render_json({
            #     "message": "success",
            #     "long_message": "uploaded %s to gcs" % goal_type,
            #     "goal_id": goal.key.id()
            # })

            self.response.out.write(str(goal.key.id()))

        else:
            logging.error("There's an error uploading an image to cloud storage")# this was added after deploy on 02/09/2015.... so if no deployment since then re-deploy and check for this error
            self.response.out.write("")
            # self.render_json({
            #     "message": "fail",
            #     "long_message": "no userid"
            # })

class APIProfileCloudStorage(MainHandler):
    def post(self):
        self.response.headers.add_header("Access-Control-Allow-Origin", '*')

        userid = self.request.get("userid")
        description = self.request.get("description")

        if userid:

            logging.error("PARAMS")
            logging.error(userid)

            user_obj = model.User.get_by_id(int(userid), parent = model.users_key())

            f = self.request.POST['image']

            #if f:
                # - - -
            serving_url = ''#just assign it adn reassign later

            logging.error("Old profile url")
            logging.error(user_obj.profile_img)

            time_stamp = time.time()

            #delete old profile image
            if user_obj.gcs_filename:
                images.delete_serving_url(blobstore.create_gs_key(user_obj.gcs_filename))
                gcs.delete(user_obj.gcs_filename[3:])

            fname = '/%s.appspot.com/user_%s_%s.jpg' % (utils.app_id, user_obj.key.id(), time_stamp)

            gcs_file = gcs.open(fname, 'w', content_type="image/jpeg")
            gcs_file.write(self.request.get('image'))
            gcs_file.close()

            gcs_filename = "/gs%s" % fname
            serving_url = images.get_serving_url(blobstore.create_gs_key(gcs_filename))

            user_obj.gcs_filename = gcs_filename
            user_obj.profile_img = serving_url
            user_obj.description = description
            user_obj.put()

            logging.error("New profile url")
            logging.error(user_obj.profile_img)

            self.render_json({
                "message": "success",
                "long_message": "uploaded profile image to gcs",
                "serving_url": serving_url
            })

        else:
            self.render_json({
                "message": "fail",
                "long_message": "no userid"
            })

class APIAddVictory(MainHandler):
    def post(self, goal_id):

        userid = self.request.get("userid")

        user_obj = False
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent = model.users_key())

        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            if user_obj.key == goal.user:
                goal.achieved = True
                goal.put()
                user_obj.total_victories += 1
                user_obj.total_points += victory_points
                utils.set_status(user_obj)
                user_obj.put()
            else:
                new_victory = utils.add_victory(user_obj, goal.image, goal.title, goal.description)

            self.render_json({
                "message": "success",
            })
        else:
            self.render_json({
                "message": "fail",
            })

class APIAddGoal(MainHandler):
    def post(self, goal_id):
        userid = self.request.get("userid")

        user_obj = False
        if userid:
            user_obj = model.User.get_by_id(int(userid), parent = model.users_key())

        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            goal_img_url = goal.image
            goal_title = goal.title
            goal_description = goal.description

            new_goal = utils.add_goal(user_obj, goal_img_url, goal_title, goal_description)

            self.render_json({
                "message": "success",
            })
        else:
            self.render_json({
                "message": "fail",
            })

class APIGetComment(MainHandler):
    def options(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

    def get(self):
        goalid = self.request.get("goalid")
        goal = model.Goal.get_by_id(int(goalid))

        userid = self.request.get("userid")
        if userid == 'undefined':
            userid = False
        if userid:
            user = model.User.get_by_id(int(userid), parent=model.users_key())
            user.has_comments = False
            user.put()

        curs = Cursor(urlsafe=self.request.get('cursor'))
        comments, next_curs, more = model.Comment.query(model.Comment.goal==goal.key).order(-model.Comment.created).fetch_page(20, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        comment_list = []
        for c in comments:
            comment_obj = {}
            comment_obj["comment"] = c.comment
            comment_obj["mentions"] = c.mentions
            comment_obj["commentor_name"] = c.user.get().name
            comment_obj["commentor_id"] = c.user.get().key.id()
            comment_list.append(comment_obj)

        self.render_json({
            "comments": comment_list,
            "next": next
        })

class APIAddComment(MainHandler):
    def options(self):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'

    def post(self):
        userid = self.request.get("userid")
        goalid = self.request.get("goalid")
        comment = self.request.get("comment")

        user = model.User.get_by_id(int(userid), parent=model.users_key())

        goal = model.Goal.get_by_id(int(goalid))

        goal.has_comments = True
        if not goal.comment_count:
            goal.comment_count = 1
        else:
            goal.comment_count += 1

        logging.error("RECENT COMMENT")
        if comment:
            logging.error("recent comment")
            logging.error(comment)
            goal.recent_comment = comment

        goal.put()

        if comment:

            mentions = [word for word in comment.split() if word.startswith('@')]
            users_mentioned = []
            for m in mentions:
                user_name = m.replace("@", "")
                existing_user = model.User.query(model.User.name == user_name).get()
                if existing_user:
                    mention_obj = {}
                    mention_obj['name'] = m
                    mention_obj['id'] = existing_user.key.id()
                    users_mentioned.append(mention_obj)

                    if not existing_user.notifications:
                        existing_user.notifications = 1
                    else:
                        existing_user.notifications += 1
                    existing_user.has_notifications = False
                    existing_user.put()

                    message = ' has has mentioned you in '
                    note = model.Notification(mention=True, type="mention", message=message, user=existing_user.key, goal=goal.key, goal_title=goal.title, trigger_user=user.key, trigger_user_name=user.name)
                    note.put()

            #logging.error(users_mentioned)
            #for u in users_mentioned:
            #    #logging.error(u)
            #    comment = comment.replace(u['name'], """<a href='#/tab/profile/%s'>%s</a>""" % (u['id'], u['name']))

            cmt = model.Comment(comment=comment, goal=goal.key, user=user.key, mentions=users_mentioned)
            cmt.put()

            notified_user = goal.user.get()
            if not notified_user.notifications:
                notified_user.notifications = 1
            else:
                notified_user.notifications += 1
            notified_user.has_notifications = False
            notified_user.put()

            if goal.achieved:
                message = ' has commented on '
            else:
                message = ' has commented on '
            note = model.Notification(comment=True, comment_key=cmt.key, type="comment", message=message, user=notified_user.key, goal=goal.key, goal_title=goal.title, trigger_user=user.key, trigger_user_name=user.name)
            note.put()

        self.render_json({
            "message": "success",
        })

class APIAddLike(MainHandler):
    def post(self):
        goal_id = self.request.get("goal_id")
        userid = self.request.get("userid")
        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())
        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))
            liked = model.Like.query( model.Like.user == user_obj.key, model.Like.goal == goal.key ).get()
            # if not liked and goal.user != user_obj.key:
            if goal.user != user_obj.key:
                if not liked:
                    goal.likes += 1;
                    goal.put()

                    like = model.Like( user = user_obj.key, goal = goal.key )
                    like.put()

                    notified_user = goal.user.get()
                    if not notified_user.notifications:
                        notified_user.notifications = 1
                    else:
                        notified_user.notifications += 1
                    notified_user.has_notifications = False
                    notified_user.put()

                    message = ' likes your goal '
                    note = model.Notification(like=True, type="like", message=message, user=notified_user.key, goal=goal.key, goal_title=goal.title, trigger_user=user_obj.key, trigger_user_name=user_obj.name)
                    note.put()


        obj = {
            'likes': goal.likes
        }
        self.render_json(obj)

class APILoggedInUserDetails(MainHandler):
    def get(self, userid):
        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

        self.render_json({
            "has_notifications": user_obj.has_notifications,
            "notification_count": user_obj.notifications,
            "has_comments": user_obj.has_notifications,
            "comment_count": user_obj.notifications,
            "has_mentions": user_obj.has_notifications,
            "mention_count": user_obj.notifications,
            "new_followers": user_obj.has_notifications,
            "new_followers_count": user_obj.notifications,
            })

class APIUserNotifications(MainHandler):
    def get(self, userid):
        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

        num_items = 20

        curs = Cursor(urlsafe=self.request.get('cursor'))
        notifications, next_curs, more = model.Notification.query(model.Notification.user==user_obj.key).order(-model.Notification.created).fetch_page(num_items, start_cursor=curs)

        if more and next_curs:
            next = next_curs.urlsafe()
        else:
            next = False

        #notifications = model.Notification.query(model.Notification.user==user_obj.key).order(-model.Notification.created).fetch()

        notification_list = []
        for n in notifications:
            try:
                note_obj = {}
                note_obj["note"] = n.message
                note_obj["type"] = n.type
                note_obj["id"] = n.key.id()
                note_obj["trigger_user"] = n.trigger_user.get().key.id()
                note_obj["trigger_user_name"] = n.trigger_user.get().name
                note_obj["profile_img"] = n.trigger_user.get().profile_img
                if n.comment_key:
                    cmt = n.comment_key.get()
                    note_obj["comment_id"] = cmt.key.id()
                    note_obj["comment_text"] = cmt.comment
                if n.goal:
                    goal = n.goal.get()
                    note_obj["goalid"] = goal.key.id()
                    note_obj["goal_title"] = goal.title
                    note_obj["goal_image"] = goal.image
                notification_list.append(note_obj)
            except:
                logging.error("Notification error - except")
                logging.error("try get trigger user")
                try:
                    logging.error(n.trigger_user.get().key.id())
                except:
                    logging.error("failed to get trigger user")
                logging.error("try get notification goal")
                try:
                    logging.error(n.goal.get().key.id())
                except:
                    logging.error("failed to get notification goal")

        user_obj.has_notifications = False
        user_obj.notifications = 0
        user_obj.put()

        self.render_json({
            "next": next,
            "notifications": notification_list,
            "number": user_obj.notifications,
            })

class APIRemoveUserNotifications(MainHandler):
    def post(self, userid):
        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())
        notification_id = self.request.get("notification_id")
        notification = model.Notification.get_by_id(int(notification_id))
        notification.key.delete()

        self.render_json({
            "message": "success"
            })

# class APIEditGoal(MainHandler):
#     def post(self, goal_id):
#         goal = model.Goal.get_by_id(int(goal_id))

#         title = self.request.get("title")
#         description = self.request.get("description")

#         goal.title = title
#         goal.description = description
#         goal.put()

#         self.render_json({
#             'message': "success"
#             })

class APIEditGoal(MainHandler):
    def post(self, goal_id):
        goal = model.Goal.get_by_id(int(goal_id))

        self.response.headers.add_header("Access-Control-Allow-Origin", '*')

        goal_title = self.request.get("title")
        goal_description = self.request.get("description")

        try:
            f = self.request.get('image')
        except:
            f = False

        if f:
            serving_url = ''#just assign it adn reassign later

            time_stamp = time.time()
            fname = '/%s.appspot.com/goal_%s_%s.jpg' % ( utils.app_id, goal.key.id(), time_stamp)

            # logging.error("file found, uploading to gcs")
            # logging.error(fname)

            gcs_file = gcs.open(fname, 'w', content_type="image/jpeg")
            gcs_file.write(self.request.get('image'))
            gcs_file.close()

            gcs_filename = "/gs%s" % fname
            serving_url = images.get_serving_url(blobstore.create_gs_key(gcs_filename))

            # logging.error("old serving url")
            # logging.error(goal.image)
            # logging.error("new serving url")
            # logging.error(serving_url)

            goal.gcs_filename = gcs_filename

            goal.image = serving_url

            msg = "with new image"
        else:
            msg = "without new image"

        goal.title = goal_title
        goal.description = goal_description
        goal.put()

        self.render_json({
            "message": "success",
            "long_message": "completed edit: %s" % msg
        })

class APIDeleteGoal(MainHandler):
    def post(self, goal_id):
        userid = self.request.get("userid")
        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())
        if user_obj:
            goal = model.Goal.get_by_id(int(goal_id))

            # not deleting images in case other users have pinned the images for their own goals

            # uploaded_image = model.Image.query( model.Image.goal == goal.key ).get()#only for single image
            # if uploaded_image:
            #     images.delete_serving_url(uploaded_image.blob_key)#delete serving url
            #     blb = blobstore.BlobInfo.get(uploaded_image.blob_key)#delete blob info which deletes blob
            #     if blb:
            #         blb.delete()#delete blob info which deletes blob
            #     uploaded_image.key.delete()

            # if goal.gcs_filename:
            #     images.delete_serving_url(blobstore.create_gs_key(goal.gcs_filename))
            #     gcs.delete(goal.gcs_filename[3:])

            # if goal.vic_gcs_filenames:
            #     for f in goal.vic_gcs_filenames:
            #         images.delete_serving_url(blobstore.create_gs_key(f))
            #         gcs.delete(f[3:])

            #also not deleting the comments/notifications so can potentially retrieve comments/notifications for records later


            if goal.achieved:
                user_obj.total_victories -= 1;
            else:
                user_obj.total_goals -= 1;
            user_obj.put()

            goal.key.delete()

            self.response.headers['Content-Type'] = 'application/json'
            self.response.headers['Host'] = 'localhost'
            self.response.headers['Access-Control-Allow-Origin'] = '*'
            obj = {
                'goal_id': goal_id,
            }
            self.response.out.write(json.dumps(obj))
        else:
            self.redirect("/login")

class APIForgotPassword(MainHandler):
    def post(self):
        email = self.request.get("recovery_email")

        user_obj = model.User.by_email(email)

        if user_obj:
            message = "your new password has been emailed to %s" % email
            utils.generate_new_password(email)
        else:
            message = "there is no user registered with the email: %s" % email

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class APIChangeEmail(MainHandler):
    def post(self):
        password = self.request.get("password")
        old_email = self.request.get("old_email")
        new_email = self.request.get("new_email")
        userid = self.request.get("userid")

        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())
        user_obj_email = model.User.by_email(old_email)

        email_verify = False
        if user_obj.key.id() == user_obj_email.key.id():
            email_verify = True

        if user_obj and email_verify:
            if user_obj.email == old_email:
                s = model.User.login(old_email, password)
                if s:
                    if not utils.valid_email(new_email):
                        message = "invalid email"
                    else:
                        new_pw_hash = utils.make_pw_hash(new_email, password)
                        user_obj.email = new_email
                        user_obj.pw_hash = new_pw_hash
                        user_obj.put()
                        message = "success"
                else:
                    message = "invalid email password combination"
            else:
                message = "invalid old email"
        else:
            message = "not logged in"

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class APIChangePassword(MainHandler):
    def post(self):
        old_password = self.request.get("old_password")
        new_password = self.request.get("new_password")
        repeat_password = self.request.get("repeat_password")
        userid = self.request.get("userid")

        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

        if user_obj:
            if new_password == repeat_password:
                s = model.User.login(user_obj.email, old_password)
                if s:
                    if not utils.valid_password(new_password):
                        message = "invalid password"
                    else:
                        new_pw_hash = utils.make_pw_hash(user_obj.email, new_password)
                        user_obj.pw_hash = new_pw_hash
                        user_obj.put()
                        message = "success"
                else:
                    message = "invalid password"
            else:
                message = "new passwords don't match"
        else:
            message = "not logged in"

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
        }
        self.response.out.write(json.dumps(obj))

class APIChangeDescription(MainHandler):
    def post(self):
        description = self.request.get("description")
        userid = self.request.get("userid")

        user_obj = model.User.get_by_id(int(userid), parent=model.users_key())

        if description:
            user_obj.description = description
            user_obj.put()

        message = 'success'

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'message': message,
            "long_message": "saved description"
        }
        self.response.out.write(json.dumps(obj))

class APISearchUser(MainHandler):
    def get(self):
        username = self.request.get("username")
        user = model.User.query(model.User.name == username).get()

        user_obj = False

        if user:
            user_obj = {}
            user_obj["name"] = user.name
            user_obj["id"] = user.key.id()
            user_obj["description"] = user.description
            user_obj["profile_img"] = user.profile_img
            user_obj["total_goals"] = user.total_goals
            user_obj["total_victories"] = user.total_victories
            user_obj["total_followers"] = user.total_followers
            user_obj["total_following"] = user.total_following

        self.render_json(user_obj)

class APILikes(MainHandler):
    def get(self, goal_id):
        goal = model.Goal.get_by_id(int(goal_id))

        likes_for_goal = model.Like.query(model.Like.goal == goal.key).fetch()

        users = []

        for l in likes_for_goal:
            user_obj = {}
            user = l.user.get()
            user_obj["name"] = user.name
            user_obj["id"] = user.key.id()
            user_obj["profile_img"] = user.profile_img
            users.append(user_obj)

        self.render_json({
            "message": "success",
            "users": users
            })


class AdminDelete(MainHandler):
    def post(self):
        goal_id = self.request.get("goal_id")
        goal = model.Goal.get_by_id(int(goal_id))

        user_obj = goal.user.get()

        uploaded_image = model.Image.query( model.Image.goal == goal.key ).get()#only for single image
        if uploaded_image:
            images.delete_serving_url(uploaded_image.blob_key)#delete serving url
            blb = blobstore.BlobInfo.get(uploaded_image.blob_key)#delete blob info which deletes blob
            if blb:
                blb.delete()#delete blob info which deletes blob
            uploaded_image.key.delete()

        user_obj.total_goals -= 1;
        user_obj.put()

        goal.key.delete()

        self.response.headers['Content-Type'] = 'application/json'
        self.response.headers['Host'] = 'localhost'
        self.response.headers['Access-Control-Allow-Origin'] = '*'
        obj = {
            'goal_id': goal_id,
            "message": 'success',
            "long_message": "admin goal delete"
        }
        self.response.out.write(json.dumps(obj))

class PrivacyPolicy(MainHandler):
    def get(self):
        self.render("privacy_policy.html")




# =============================
# Admin
# =============================

class Admin(MainHandler):
    def get(self):
        count = model.Count.query().get()
        if not count:
            count = model.Count()
            count.put()
        self.render("cms.html", count=count)

class AdminUser(MainHandler):
    def get(self, user_id):
        user_obj = model.User.get_by_id(int(user_id), parent = model.users_key())
        self.render("/admin/admin-user.html", user_obj=user_obj)

class AdminUsers(MainHandler):
    def get(self):
        curs = Cursor(urlsafe=self.request.get('cursor'))
        users, next_curs, more = model.User.query().order(-model.User.total_points).fetch_page(50, start_cursor=curs)
        if more and next_curs:
            next_curs = next_curs.urlsafe()
        else:
            next_curs = False

        self.render("/admin/users.html", users=users, next_curs=next_curs)

class AdminCountryExplorer(MainHandler):
    def get(self):
        self.render("/admin/country-explorer.html")

class AdminCountryList(MainHandler):
    def get(self):
        countries = model.Country.query().fetch(use_cache=False, use_memcache=False)

        self.render("/admin/country-list.html", countries=countries)

class AdminCountryExplorerGoals(MainHandler):
    def get(self):

        name_email = self.request.get("name_email")

        more = False
        if name_email:
            user = model.User.query(model.User.name == name_email).get()
            if not user:
                user = model.User.query(model.User.email == name_email).get()
            if user:
                curs = Cursor(urlsafe=self.request.get('cursor'))
                goals, next_curs, more = model.Goal.query(model.Goal.curated == False, model.Goal.user == user.key).order(-model.Goal.created).fetch_page(20, start_cursor=curs)
            else:
                goals = None
        else:
            curs = Cursor(urlsafe=self.request.get('cursor'))
            goals, next_curs, more = model.Goal.query(model.Goal.curated == False).order(-model.Goal.created).fetch_page(20, start_cursor=curs)

        countries = utils.countries

        curator_obj = model.User.query(model.User.email == curator_email).get()
        curator_id = curator_obj.key.id()

        if more and next_curs:
            next_curs = next_curs.urlsafe()
        else:
            next_curs = False
        self.render("/admin/country-explorer-goals.html", goals=goals, next_curs=next_curs, countries=countries, curator_id=curator_id, name_email=name_email)

class AdminCountryExplorerCurated(MainHandler):
    def get(self):

        country = self.request.get("country")
        country_code = country
        country_obj = None

        curs = Cursor(urlsafe=self.request.get('cursor'))
        goals = None
        next_curs = False
        if country:
            country_obj = model.Country.query(model.Country.countryCode == country).get()
            if country_obj:
                country_key = country_obj.key
                goals, next_curs, more = model.Goal.query( model.Goal.curated==True, model.Goal.country_key == country_key ).order(-model.Goal.created).fetch_page(20, start_cursor=curs)

                if more and next_curs:
                    next_curs = next_curs.urlsafe()
                else:
                    next_curs = False

            # else:
            #     goals, next_curs, more = model.Goal.query( model.Goal.curated==True ).order(-model.Goal.created).fetch_page(20, start_cursor=curs)
        else:
            goals, next_curs, more = model.Goal.query( model.Goal.curated==True ).order(-model.Goal.created).fetch_page(20, start_cursor=curs)

            if more and next_curs:
                next_curs = next_curs.urlsafe()
            else:
                next_curs = False

        countries = utils.countries

        curator_obj = model.User.query(model.User.email == curator_email).get()
        curator_id = curator_obj.key.id()

        self.render("/admin/country-explorer-curated-goals.html", goals=goals, next_curs=next_curs, countries=countries, curator_id=curator_id, country=country_obj, country_code=country_code)

# class AdminCountryExplorerNormalCurated(MainHandler):
#     def post(self):
#         goal_id = self.request.get("goal_id")

#         goal = model.Goal.get_by_id(int(goal_id))
#         goal.curated = True
#         goal.put()

#         self.render_json({
#             "goal_id": goal_id
#             })

class AdminCountryExplorerNewCuratedGoal(MainHandler):
    def get(self):
        countries = utils.countries
        self.render("/admin/admin-new-curated-goal.html", countries=countries)
    def post(self):
        title = self.request.get("title")
        description = self.request.get("description")
        image = self.request.get("image")
        country = self.request.get("country")

        country = utils.get_country(country)

        user = model.User.query(model.User.email == curator_email).get()

        if user:
            user_key = user.key
            bv_goal = True
            goal = model.Goal( title=title, description=description, user=user_key, curated=True, country_key=country.key, country_name=country.countryName, country_code=country.countryCode )
            goal.put()

            if country:
                country.number_goals += 1
                country.put()

            goal = utils.save_to_gcs(goal, image)

            # origin_user = goal.user
            # origin_user_id = str( goal.user.get().key.id() )
            # origin_goal = goal.key
            # origin_goal_id = str( goal.key.id() )

            # image = goal.image
            # gcs_filename = goal.gcs_filename
            # likes = goal.likes
            # views = goal.views

            # curated_goal = model.Goal(
            #     origin_user=origin_user,
            #     origin_user_id=origin_user_id,
            #     origin_goal=origin_goal,
            #     origin_goal_id=origin_goal_id,
            #     image=image,
            #     gcs_filename=gcs_filename,
            #     likes=likes,
            #     views=views,
            #     title=title,
            #     description=description,
            #     user=user_key,
            #     bv_goal=bv_goal)
            # curated_goal.put()

            # JSON response ---- working
            # self.render_json({
            #     "message": "success",
            #     "goal_id": goal.key.id()
            #     # "curated_goal_id": curated_goal.key.id()
            #     })

            self.redirect("/admin/country_explorer/curated")

        else:
            # self.render_json({
            #     "message": "fail",
            #     "long_message": "no user"
            #     })
            self.redirect("/admin/country_explorer/curated/new?error=no_bv_user")




class AdminAddCuratedGoal(MainHandler):
    def post(self, goal_id):
        title = self.request.get("title")
        description = self.request.get("description")
        bv_post = self.request.get("bv_post")
        country = self.request.get("country")

        goal = model.Goal.get_by_id(int(goal_id))

        country = utils.get_country(country)

        if goal:

            # origin_user = goal.user
            # origin_user_id = str( goal.user.get().key.id() )
            # origin_goal = goal.key
            # origin_goal_id = str( goal.key.id() )

            # image = goal.image
            # gcs_filename = goal.gcs_filename
            # likes = goal.likes
            # views = goal.views

            # title = title
            # description = description
            bv_goal = False

            logging.error("bv_post.................... %s" % bv_post)

            if not bv_post:
                user_key = goal.user
            else:
                user = model.User.query(model.User.email == curator_email).get()
                user_key = user.key
                bv_goal = True
                # take existing image url from old goal
                image = goal.image
                #reset goal variable
                goal = utils.add_goal(user, image, title, description)
                #goal.put()

            # curated_goal = model.CuratedGoal(
            #     origin_user=origin_user,
            #     origin_user_id=origin_user_id,
            #     origin_goal=origin_goal,
            #     origin_goal_id=origin_goal_id,
            #     image=image,
            #     gcs_filename=gcs_filename,
            #     likes=likes,
            #     views=views,
            #     title=title,
            #     description=description,
            #     user=user_key,
            #     bv_goal=bv_goal)
            # curated_goal.put()

            goal.curated = True
            goal.country_key = country.key
            goal.country_name = country.countryName
            goal.country_code = country.countryCode
            goal.put()

            if country:
                country.number_goals += 1
                country.put()

            # JSON response ---- working
            # self.render_json({
            #     "message": "success",
            #     "goal_id": goal_id
            #     # "curated_goal_id": curated_goal.key.id()
            #     })

            self.redirect("/admin/country_explorer/curated")

class AdminEditCuratedGoal(MainHandler):
    def post(self, goal_id):
        title = self.request.get("title")
        description = self.request.get("description")

        country = self.request.get("country")

        delete = self.request.get("delete")

        country = utils.get_country(country)

        goal = model.Goal.get_by_id(int(goal_id))
        country_to_check = goal.country_key.get()

        try:
            if country_to_check:
                if country_to_check.key == country.key:
                    logging.error("country stays the same don't increment / decrement the num of goals")
                else:
                    country_to_check.number_goals -= 1
                    country_to_check.put()
        except:
            logging.error("AdminEditCuratedGoal - error decrementing country total goals on edit")

        # utils.check_countries( goal.country_key.get() )

        if goal:
            deleted = False
            if delete:
                try:
                    country_to_edit = model.Country.get_by_id( int(goal.country_key.id()) )
                    if country_to_edit:
                        country_to_edit.number_goals -= 1
                        country_to_edit.put()
                except:
                    logging.error("AdminEditCuratedGoal - error decrementing country total goals on delete")

                if goal.user.get().email == curator_email:
                    goal.key.delete()
                    deleted = True
                else:
                    goal.curated = False
                    deleted = True
                    goal.put()
            else:
                goal.description = description
                goal.title = title
                goal.country_key = country.key
                goal.country_name = country.countryName
                goal.country_code = country.countryCode
                goal.put()

                try:
                    country.number_goals += 1
                    country.put()
                except:
                    logging.error("AdminEditCuratedGoal - error adding a goal to the new country")

            utils.check_countries( country_to_check )

            self.render_json({
                "message": "success",
                "curated_goal_id": goal_id,
                "deleted": deleted
                })

class TaskTrigger(MainHandler):
    def get(self):
        taskqueue.add(url='/task_curated_false')
        self.response.out.write("task started... I think")

class TaskCuratedFalse(MainHandler):
    def post(self):

        def goals_to_curate(curs):
            goals, next_curs, more = model.Goal.query().order().fetch_page(500, start_cursor=curs)
            for g in goals:
                g.curated = False
                g.put()
            if more and next_curs:
                goals_to_curate(next_curs)
            else:
                self.response.out.write("done auto curating")

        curs = Cursor(urlsafe=self.request.get('cursor'))
        goals_to_curate(curs)

        #goals, next_curs, more = model.Goal.query().order().fetch_page(load_goal_num, start_cursor=curs)


app = webapp2.WSGIApplication([
    ('/', HomePage),
    ('/country_explorer', CountryExplorer),
    ('/how_it_works', HowItWorks),
    ('/page_goals', PageGoals),
    ('/page_feed_goals', PageFeed),
    ('/g/(\w+)', GoalPage),
    ('/goals', Visions),
    ('/victories', Victories),
    ('/settings', Settings),
    ('/feed', Feed),
    ('/get_user_profile/(\w+)', GetUserProfile),
    ('/get_goal_profile/(\w+)', GetGoalProfile),
    ('/edit_goal/(\w+)', EditGoal),
    ('/edit_title_description', EditTitleDescription),
    ('/save_img_pos', ImgPos),
    ('/follow/(\w+)', Follow),
    ('/unfollow/(\w+)', UnFollow),
    ('/add_goal', AddGoal),
    ('/add_goal_ajax', AddGoalAjax),
    ('/delete_goal', DeleteGoal),
    ('/steal_goal', StealGoal),
    ('/steal_victory', StealVictory),
    ('/add_victory/(\w+)', AddVictory),
    ('/add_view/(\w+)', AddView),
    ('/add_like/(\w+)', AddLike),
    ('/add_board', AddBoard),
    ('/upload_profile_img/(\w+)', UploadProfileImage),
    ('/upload_goal_img/(\w+)/(\w+)/(\w+)', UploadGoalImage),
    ('/upload_vic_img/(\w+)/(\w+)', UploadVictoryImage),
    ('/upload_goal_edit_img/(\w+)/(\w+)', UploadEditImage),
    ('/add_vic_img_url', UploadVicImage),
    ('/add_vic_vid', AddVicVid),
    ('/make_cover', MakeCover),
    ('/delete_media', DeleteMedia),
    ('/add_victory_media/(\w+)', VictoryMedia),
    ('/get_upload_url', BlobUploadUrl),
    ('/victory_album/(\w+)', VictoryAlbum),

    ('/goals/(\w+)', UserGoals),
    ('/victories/(\w+)', UserVictories),

    ('/share_point', SharePoint),

    ('/login', Login),
    ('/logout', Logout),
    ('/register', Register),
    ('/forgot_password', ForgotPassword),
    ('/change_password', ChangePassword),
    ('/change_email', ChangeEmail),
    ('/delete_account', DeleteAccount),
    ('/search_users', SearchUsers),

    ('/save_video', SaveVideo),
    #('/populate_profile_images', PopulateProfile),

    # ================
    # ADMIN
    # ================
    ('/admin', Admin),
    ('/admin/users', AdminUsers),
    ('/admin/user/(\w+)', AdminUser),
    ('/admin/country_explorer', AdminCountryExplorer),
    ('/admin/country_explorer/countries', AdminCountryList),
    ('/admin/country_explorer/goals', AdminCountryExplorerGoals),
    ('/admin/country_explorer/curated', AdminCountryExplorerCurated),
    # ('/admin/country_explorer/add_normal_goal', AdminCountryExplorerNormalCurated),
    ('/admin/country_explorer/curated/new', AdminCountryExplorerNewCuratedGoal),
    ('/admin/country_explorer/add_goal/(\w+)', AdminAddCuratedGoal),
    ('/admin/country_explorer/edit_goal/(\w+)', AdminEditCuratedGoal),

    ('/leaderboard', LeaderBoard),
    ('/admin_manage_goals', AdminManageGoals),
    #admin delete button
    ('/admin_delete', AdminDelete),
    # taskqueue
    # ('/task_trigger', TaskTrigger),
    # ('/task_curated_false', TaskCuratedFalse),

    #API
    ('/api/register', APIRegister),
    ('/api/profile_img', APIProfileCloudStorage),
    ('/api/login', APILogin),
    ('/api/goals', APIGoals),
    ('/api/get_countries', APICountries),
    ('/api/inspirations', APIInspirations),
    ('/api/news', APINews),
    ('/api/goal/(\w+)', APIGoal),
    ('/api/goals/general', APIGetGoalGeneral),
    ('/api/user/(\w+)', APIUser),
    ('/api/followers/(\w+)', APIFollowers),
    ('/api/following/(\w+)', APIFollowing),
    ('/api/follow/(\w+)', APIFollow),
    ('/api/unfollow/(\w+)', APIUnFollow),
    ('/api/save_image', APICloudStorage),
    ('/api/add_victory/(\w+)', APIAddVictory),
    ('/api/add_goal/(\w+)', APIAddGoal),
    ('/api/get_comment', APIGetComment),
    ('/api/add_comment', APIAddComment),
    ('/api/add_like', APIAddLike),
    ('/api/notifications/(\w+)', APIUserNotifications),
    ('/api/remove_notifications/(\w+)', APIRemoveUserNotifications),
    ('/api/edit/(\w+)', APIEditGoal),
    ('/api/delete/(\w+)', APIDeleteGoal),
    ('/api/search_user', APISearchUser),
    ('/api/likes/(\w+)', APILikes),

    ('/api/forgot_password', APIForgotPassword),
    ('/api/change_password', APIChangePassword),
    ('/api/change_email', APIChangeEmail),
    ('/api/change_description', APIChangeDescription),

    ('/privacy', PrivacyPolicy),

], debug=False)
