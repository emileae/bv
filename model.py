from google.appengine.ext import ndb

import utils

def users_key(group='default'):
    return ndb.Key('users', group)

class User(ndb.Model):
    name = ndb.StringProperty()
    description = ndb.TextProperty()
    email = ndb.StringProperty()
    pw_hash = ndb.StringProperty()
    fb_accesstoken = ndb.StringProperty()
    fb_uid = ndb.StringProperty()
    total_points = ndb.IntegerProperty(default=0)
    status = ndb.StringProperty(default="beginner")
    total_goals = ndb.IntegerProperty(default=0)
    total_followers = ndb.IntegerProperty(default=0)
    total_following = ndb.IntegerProperty(default=0)#this is newly added
    total_victories = ndb.IntegerProperty(default=0)
    gcs_filename = ndb.StringProperty()
    profile_img = ndb.StringProperty(default="/static/images/profile.jpg")
    img_top = ndb.StringProperty()

    has_comments = ndb.BooleanProperty(default=False)
    comment_count = ndb.IntegerProperty(default=0)

    has_mentions = ndb.BooleanProperty(default=False)
    mention_count = ndb.IntegerProperty(default=0)

    new_followers = ndb.BooleanProperty(default=False)
    new_followers_count = ndb.IntegerProperty(default=0)

    has_notifications = ndb.BooleanProperty(default=False)
    notifications = ndb.IntegerProperty(default=0)

    @classmethod
    def by_id(cls, uid):
        return cls.get_by_id(uid, parent = users_key())

    @classmethod
    def login(cls, email, pw):
        u = cls.by_email(email)
        if u:
            email = u.email
        if u and utils.valid_pw(email, pw, u.pw_hash):
            return u

    @classmethod
    def fb_login(cls, uid, access_token):
        u = cls.by_fb_uid(uid)
        if u:
            uid = u.fb_uid
            return u
        #if u and utils.valid_pw(uid, access_token, u.pw_hash):
        #    return u

    @classmethod
    def by_email(cls, email):
        u = User.query(User.email == email).get()
        return u

    @classmethod
    def by_fb_uid(cls, uid):
        u = User.query(User.fb_uid == uid).get()
        return u

class Goal(ndb.Model):
    image = ndb.StringProperty()
    gcs_filename = ndb.StringProperty()
    img_top = ndb.StringProperty()
    title = ndb.StringProperty()
    description = ndb.TextProperty()
    likes = ndb.IntegerProperty(default=0)
    views = ndb.IntegerProperty(default=0)
    user = ndb.KeyProperty(User)
    achieved = ndb.BooleanProperty(default=False)
    vic_pics = ndb.StringProperty(repeated=True)
    vic_gcs_filenames = ndb.StringProperty(repeated=True)
    vic_vids = ndb.StringProperty(repeated=True)

    has_comments = ndb.BooleanProperty(default=False)
    comment_count = ndb.IntegerProperty(default=0)
    recent_comment = ndb.TextProperty()

    curated = ndb.BooleanProperty(default=False)
    country_key = ndb.KeyProperty()
    country_name = ndb.StringProperty()
    country_code = ndb.StringProperty()

    # website = ndb.StringProperty()

    created = ndb.DateTimeProperty(auto_now_add=True)

# class CuratedGoal(ndb.Model):
#     origin_user = ndb.KeyProperty(kind="User")
#     origin_user_id = ndb.StringProperty()
#     origin_goal = ndb.KeyProperty(kind="Goal")
#     origin_goal_id = ndb.StringProperty()
#     bv_goal = ndb.BooleanProperty(default=False)

#     image = ndb.StringProperty()
#     gcs_filename = ndb.StringProperty()
#     img_top = ndb.StringProperty()
#     title = ndb.StringProperty()
#     description = ndb.TextProperty()
#     likes = ndb.IntegerProperty(default=0)
#     views = ndb.IntegerProperty(default=0)
#     user = ndb.KeyProperty(User)

#     #these wont be used
#     achieved = ndb.BooleanProperty(default=False)
#     vic_pics = ndb.StringProperty(repeated=True)
#     vic_gcs_filenames = ndb.StringProperty(repeated=True)
#     vic_vids = ndb.StringProperty(repeated=True)

#     #preserving comments
#     has_comments = ndb.BooleanProperty(default=False)
#     comment_count = ndb.IntegerProperty(default=0)
#     recent_comment = ndb.TextProperty()

#     curated = ndb.BooleanProperty(default=True)

#     created = ndb.DateTimeProperty(auto_now_add=True)

class Country(ndb.Model):
    countryCode = ndb.StringProperty()
    countryName = ndb.StringProperty()
    number_goals = ndb.IntegerProperty(default=0)
    created = ndb.DateTimeProperty(auto_now_add=True)

class Count(ndb.Model):
    users = ndb.IntegerProperty(default=658)
    created = ndb.DateTimeProperty(auto_now_add=True)

class Like(ndb.Model):
    user = ndb.KeyProperty(User)
    goal = ndb.KeyProperty(Goal)

class Follow(ndb.Model):
    followed = ndb.KeyProperty(User)
    following = ndb.KeyProperty(User)

class Image(ndb.Model):
    user = ndb.KeyProperty(User)
    img_type = ndb.StringProperty()
    goal = ndb.KeyProperty(Goal)
    serving_url = ndb.StringProperty()
    blob_key = ndb.BlobKeyProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

class Comment(ndb.Model):
    comment = ndb.TextProperty()
    user = ndb.KeyProperty(kind="User")
    goal = ndb.KeyProperty(kind="Goal")
    mentions = ndb.JsonProperty(repeated=True)
    created = ndb.DateTimeProperty(auto_now_add=True)

class Notification(ndb.Model):
    user = ndb.KeyProperty(kind="User")
    message = ndb.StringProperty()
    type = ndb.StringProperty()
    follow = ndb.BooleanProperty(default=False)
    comment = ndb.BooleanProperty(default=False)
    comment_key = ndb.KeyProperty(kind="Comment")
    like = ndb.BooleanProperty(default=False)
    mention = ndb.BooleanProperty(default=False)

    trigger_user = ndb.KeyProperty(kind="User")
    trigger_user_name = ndb.StringProperty()
    goal = ndb.KeyProperty(kind="Goal")
    goal_title = ndb.StringProperty()

    created = ndb.DateTimeProperty(auto_now_add=True)
