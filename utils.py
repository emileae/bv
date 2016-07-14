
import re
import hashlib
import hmac
import random
import string
from string import letters
import logging
import urllib2
import json
import time

from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.api import images
from google.appengine.api import urlfetch
from google.appengine.api import mail

from google.appengine.api import app_identity
import cloudstorage as gcs

from urlparse import urlparse
try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs
    urlparse.parse_qs = parse_qs

import model

secret = 'BucK3tViSi0n'
MANDRILL_KEY= "6-4qABXLxL46ELS2tvZS8A"#"lemQSSH7tBEqsXRcdmTgfg"
app_id = app_identity.get_application_id()
#sender_email = "bucketvision1@gmail.com"
sender_email = "bucketvision1@gmail.com"
goal_points = 1
victory_points = 5
base_url = "http://%s.appspot.com" % app_id

bucket_vision_user_id = '5698998010642432'

# ====================
# Google Cloud Storage
# ====================

def save_to_gcs(goal_obj, file_obj):
    serving_url = ''#just assign it adn reassign later
    time_stamp = int(time.time())
    app_id = app_identity.get_application_id()

    fname = '/%s.appspot.com/post_%s.jpg' % (app_id, time_stamp)

    gcs_file = gcs.open(fname, 'w', content_type="image/jpeg")
    gcs_file.write(file_obj)
    gcs_file.close()

    gcs_filename = "/gs%s" % fname
    serving_url = images.get_serving_url(blobstore.create_gs_key(gcs_filename))

    goal_obj.gcs_filename = gcs_filename
    goal_obj.image = serving_url
    goal_obj.put()

    return goal_obj


#PW HASHING
def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)
    
def make_salt(length=5):
    return ''.join(random.choice(letters) for x in xrange(length))
    
# returns a cookie with a value value|hashedvalue
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())
# returns the origional value and validates if given hashed cookie matches our hash of the value    
def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val
        
def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)


#REGEX for register validtion
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return email and EMAIL_RE.match(email)
    
        
def request_blob_url(self, callback_url, max_bytes):
    upload_url = blobstore.create_upload_url(callback_url, max_bytes)
    return upload_url
    
def save_blob_to_image_obj(blob_key, user_obj, img_type):
    if user_obj:
        user_key = user_obj.key
        serving_url = images.get_serving_url(blob_key)
        
        img = model.Image( user=user_key, serving_url=serving_url, blob_key=blob_key, img_type=img_type )
        img.put()
        
        return serving_url
    
def save_blob_to_goal_image_obj(blob_key, user_obj, img_type, goal):
    if user_obj:
        user_key = user_obj.key
        serving_url = images.get_serving_url(blob_key)
        
        img = model.Image( user=user_key, serving_url=serving_url, blob_key=blob_key, img_type=img_type, goal = goal.key )
        img.put()
        
        return serving_url
    
def save_company(user, company_name, company_website, facebook_url, twitter_url, company_type, country, city, street_address, position):
    company = model.Company( user=user.key, company_name=company_name, company_website=company_website, facebook_url=facebook_url, twitter_url=twitter_url, company_type=company_type, country=country, city=city, street_address=street_address, position=position )
    company.put()
    
    
def save_startup(name, position, user_obj):
    
    startup = model.Startups.query( model.Startups.user == user_obj.key ).get();
    
    if startup:
        startup.name = name
        startup.position = position
        startup.put()
    else:
        su = model.Startups( name=name, position=position, user=user_obj.key, phone="", website="", alt_email="", description="", twitter="", facebook="", linkedin="" )
        su.put()
    
def save_startup_details(description, website, phone, alt_email, user_obj, twitter, facebook, linkedin):
    su = model.Startups.query( model.Startups.user == user_obj.key ).get()
    
    su.description = description
    su.website = website
    su.phone = phone
    su.alt_email = alt_email
    su.twitter = twitter
    su.facebook = facebook
    su.linkedin = linkedin
    su.put()
    
def post_job(startup, title, description, deadline, phone, alt_email):
    job = model.Jobs(startup=startup.key, title=title, description=description, deadline=deadline, phone=phone,alt_email=alt_email)
    job.put()
    
    if not startup.jobs_posted:
        startup.jobs_posted = True
        startup.put()
    
    return job
    

# ===============================
# Bucket Vision
# ===============================

countries = [{"countryCode":"AF","countryName":"Afghanistan"},{"countryCode":"AX","countryName":"Aland"},{"countryCode":"AL","countryName":"Albania"},{"countryCode":"DZ","countryName":"Algeria"},{"countryCode":"AS","countryName":"American Samoa"},{"countryCode":"AD","countryName":"Andorra"},{"countryCode":"AO","countryName":"Angola"},{"countryCode":"AI","countryName":"Anguilla"},{"countryCode":"AQ","countryName":"Antarctica"},{"countryCode":"AG","countryName":"Antigua and Barbuda"},{"countryCode":"AR","countryName":"Argentina"},{"countryCode":"AM","countryName":"Armenia"},{"countryCode":"AW","countryName":"Aruba"},{"countryCode":"AU","countryName":"Australia"},{"countryCode":"AT","countryName":"Austria"},{"countryCode":"AZ","countryName":"Azerbaijan"},{"countryCode":"BS","countryName":"Bahamas"},{"countryCode":"BH","countryName":"Bahrain"},{"countryCode":"BD","countryName":"Bangladesh"},{"countryCode":"BB","countryName":"Barbados"},{"countryCode":"BY","countryName":"Belarus"},{"countryCode":"BE","countryName":"Belgium"},{"countryCode":"BZ","countryName":"Belize"},{"countryCode":"BJ","countryName":"Benin"},{"countryCode":"BM","countryName":"Bermuda"},{"countryCode":"BT","countryName":"Bhutan"},{"countryCode":"BO","countryName":"Bolivia"},{"countryCode":"BQ","countryName":"Bonaire"},{"countryCode":"BA","countryName":"Bosnia and Herzegovina"},{"countryCode":"BW","countryName":"Botswana"},{"countryCode":"BV","countryName":"Bouvet Island"},{"countryCode":"BR","countryName":"Brazil"},{"countryCode":"IO","countryName":"British Indian Ocean Territory"},{"countryCode":"VG","countryName":"British Virgin Islands"},{"countryCode":"BN","countryName":"Brunei"},{"countryCode":"BG","countryName":"Bulgaria"},{"countryCode":"BF","countryName":"Burkina Faso"},{"countryCode":"BI","countryName":"Burundi"},{"countryCode":"KH","countryName":"Cambodia"},{"countryCode":"CM","countryName":"Cameroon"},{"countryCode":"CA","countryName":"Canada"},{"countryCode":"CV","countryName":"Cape Verde"},{"countryCode":"KY","countryName":"Cayman Islands"},{"countryCode":"CF","countryName":"Central African Republic"},{"countryCode":"TD","countryName":"Chad"},{"countryCode":"CL","countryName":"Chile"},{"countryCode":"CN","countryName":"China"},{"countryCode":"CX","countryName":"Christmas Island"},{"countryCode":"CC","countryName":"Cocos [Keeling] Islands"},{"countryCode":"CO","countryName":"Colombia"},{"countryCode":"KM","countryName":"Comoros"},{"countryCode":"CK","countryName":"Cook Islands"},{"countryCode":"CR","countryName":"Costa Rica"},{"countryCode":"HR","countryName":"Croatia"},{"countryCode":"CU","countryName":"Cuba"},{"countryCode":"CW","countryName":"Curacao"},{"countryCode":"CY","countryName":"Cyprus"},{"countryCode":"CZ","countryName":"Czech Republic"},{"countryCode":"CD","countryName":"Democratic Republic of the Congo"},{"countryCode":"DK","countryName":"Denmark"},{"countryCode":"DJ","countryName":"Djibouti"},{"countryCode":"DM","countryName":"Dominica"},{"countryCode":"DO","countryName":"Dominican Republic"},{"countryCode":"TL","countryName":"East Timor"},{"countryCode":"EC","countryName":"Ecuador"},{"countryCode":"EG","countryName":"Egypt"},{"countryCode":"SV","countryName":"El Salvador"},{"countryCode":"GQ","countryName":"Equatorial Guinea"},{"countryCode":"ER","countryName":"Eritrea"},{"countryCode":"EE","countryName":"Estonia"},{"countryCode":"ET","countryName":"Ethiopia"},{"countryCode":"FK","countryName":"Falkland Islands"},{"countryCode":"FO","countryName":"Faroe Islands"},{"countryCode":"FJ","countryName":"Fiji"},{"countryCode":"FI","countryName":"Finland"},{"countryCode":"FR","countryName":"France"},{"countryCode":"GF","countryName":"French Guiana"},{"countryCode":"PF","countryName":"French Polynesia"},{"countryCode":"TF","countryName":"French Southern Territories"},{"countryCode":"GA","countryName":"Gabon"},{"countryCode":"GM","countryName":"Gambia"},{"countryCode":"GE","countryName":"Georgia"},{"countryCode":"DE","countryName":"Germany"},{"countryCode":"GH","countryName":"Ghana"},{"countryCode":"GI","countryName":"Gibraltar"},{"countryCode":"GR","countryName":"Greece"},{"countryCode":"GL","countryName":"Greenland"},{"countryCode":"GD","countryName":"Grenada"},{"countryCode":"GP","countryName":"Guadeloupe"},{"countryCode":"GU","countryName":"Guam"},{"countryCode":"GT","countryName":"Guatemala"},{"countryCode":"GG","countryName":"Guernsey"},{"countryCode":"GN","countryName":"Guinea"},{"countryCode":"GW","countryName":"Guinea-Bissau"},{"countryCode":"GY","countryName":"Guyana"},{"countryCode":"HT","countryName":"Haiti"},{"countryCode":"HM","countryName":"Heard Island and McDonald Islands"},{"countryCode":"HN","countryName":"Honduras"},{"countryCode":"HK","countryName":"Hong Kong"},{"countryCode":"HU","countryName":"Hungary"},{"countryCode":"IS","countryName":"Iceland"},{"countryCode":"IN","countryName":"India"},{"countryCode":"ID","countryName":"Indonesia"},{"countryCode":"IR","countryName":"Iran"},{"countryCode":"IQ","countryName":"Iraq"},{"countryCode":"IE","countryName":"Ireland"},{"countryCode":"IM","countryName":"Isle of Man"},{"countryCode":"IL","countryName":"Israel"},{"countryCode":"IT","countryName":"Italy"},{"countryCode":"CI","countryName":"Ivory Coast"},{"countryCode":"JM","countryName":"Jamaica"},{"countryCode":"JP","countryName":"Japan"},{"countryCode":"JE","countryName":"Jersey"},{"countryCode":"JO","countryName":"Jordan"},{"countryCode":"KZ","countryName":"Kazakhstan"},{"countryCode":"KE","countryName":"Kenya"},{"countryCode":"KI","countryName":"Kiribati"},{"countryCode":"XK","countryName":"Kosovo"},{"countryCode":"KW","countryName":"Kuwait"},{"countryCode":"KG","countryName":"Kyrgyzstan"},{"countryCode":"LA","countryName":"Laos"},{"countryCode":"LV","countryName":"Latvia"},{"countryCode":"LB","countryName":"Lebanon"},{"countryCode":"LS","countryName":"Lesotho"},{"countryCode":"LR","countryName":"Liberia"},{"countryCode":"LY","countryName":"Libya"},{"countryCode":"LI","countryName":"Liechtenstein"},{"countryCode":"LT","countryName":"Lithuania"},{"countryCode":"LU","countryName":"Luxembourg"},{"countryCode":"MO","countryName":"Macao"},{"countryCode":"MK","countryName":"Macedonia"},{"countryCode":"MG","countryName":"Madagascar"},{"countryCode":"MW","countryName":"Malawi"},{"countryCode":"MY","countryName":"Malaysia"},{"countryCode":"MV","countryName":"Maldives"},{"countryCode":"ML","countryName":"Mali"},{"countryCode":"MT","countryName":"Malta"},{"countryCode":"MH","countryName":"Marshall Islands"},{"countryCode":"MQ","countryName":"Martinique"},{"countryCode":"MR","countryName":"Mauritania"},{"countryCode":"MU","countryName":"Mauritius"},{"countryCode":"YT","countryName":"Mayotte"},{"countryCode":"MX","countryName":"Mexico"},{"countryCode":"FM","countryName":"Micronesia"},{"countryCode":"MD","countryName":"Moldova"},{"countryCode":"MC","countryName":"Monaco"},{"countryCode":"MN","countryName":"Mongolia"},{"countryCode":"ME","countryName":"Montenegro"},{"countryCode":"MS","countryName":"Montserrat"},{"countryCode":"MA","countryName":"Morocco"},{"countryCode":"MZ","countryName":"Mozambique"},{"countryCode":"MM","countryName":"Myanmar [Burma]"},{"countryCode":"NA","countryName":"Namibia"},{"countryCode":"NR","countryName":"Nauru"},{"countryCode":"NP","countryName":"Nepal"},{"countryCode":"NL","countryName":"Netherlands"},{"countryCode":"NC","countryName":"New Caledonia"},{"countryCode":"NZ","countryName":"New Zealand"},{"countryCode":"NI","countryName":"Nicaragua"},{"countryCode":"NE","countryName":"Niger"},{"countryCode":"NG","countryName":"Nigeria"},{"countryCode":"NU","countryName":"Niue"},{"countryCode":"NF","countryName":"Norfolk Island"},{"countryCode":"KP","countryName":"North Korea"},{"countryCode":"MP","countryName":"Northern Mariana Islands"},{"countryCode":"NO","countryName":"Norway"},{"countryCode":"OM","countryName":"Oman"},{"countryCode":"PK","countryName":"Pakistan"},{"countryCode":"PW","countryName":"Palau"},{"countryCode":"PS","countryName":"Palestine"},{"countryCode":"PA","countryName":"Panama"},{"countryCode":"PG","countryName":"Papua New Guinea"},{"countryCode":"PY","countryName":"Paraguay"},{"countryCode":"PE","countryName":"Peru"},{"countryCode":"PH","countryName":"Philippines"},{"countryCode":"PN","countryName":"Pitcairn Islands"},{"countryCode":"PL","countryName":"Poland"},{"countryCode":"PT","countryName":"Portugal"},{"countryCode":"PR","countryName":"Puerto Rico"},{"countryCode":"QA","countryName":"Qatar"},{"countryCode":"CG","countryName":"Republic of the Congo"},{"countryCode":"RE","countryName":"Reunion"},{"countryCode":"RO","countryName":"Romania"},{"countryCode":"RU","countryName":"Russia"},{"countryCode":"RW","countryName":"Rwanda"},{"countryCode":"BL","countryName":"Saint Barthelemy"},{"countryCode":"SH","countryName":"Saint Helena"},{"countryCode":"KN","countryName":"Saint Kitts and Nevis"},{"countryCode":"LC","countryName":"Saint Lucia"},{"countryCode":"MF","countryName":"Saint Martin"},{"countryCode":"PM","countryName":"Saint Pierre and Miquelon"},{"countryCode":"VC","countryName":"Saint Vincent and the Grenadines"},{"countryCode":"WS","countryName":"Samoa"},{"countryCode":"SM","countryName":"San Marino"},{"countryCode":"ST","countryName":"Sao Tome and Principe"},{"countryCode":"SA","countryName":"Saudi Arabia"},{"countryCode":"SN","countryName":"Senegal"},{"countryCode":"RS","countryName":"Serbia"},{"countryCode":"SC","countryName":"Seychelles"},{"countryCode":"SL","countryName":"Sierra Leone"},{"countryCode":"SG","countryName":"Singapore"},{"countryCode":"SX","countryName":"Sint Maarten"},{"countryCode":"SK","countryName":"Slovakia"},{"countryCode":"SI","countryName":"Slovenia"},{"countryCode":"SB","countryName":"Solomon Islands"},{"countryCode":"SO","countryName":"Somalia"},{"countryCode":"ZA","countryName":"South Africa"},{"countryCode":"GS","countryName":"South Georgia"},{"countryCode":"KR","countryName":"South Korea"},{"countryCode":"SS","countryName":"South Sudan"},{"countryCode":"ES","countryName":"Spain"},{"countryCode":"LK","countryName":"Sri Lanka"},{"countryCode":"SD","countryName":"Sudan"},{"countryCode":"SR","countryName":"Suriname"},{"countryCode":"SJ","countryName":"Svalbard and Jan Mayen"},{"countryCode":"SZ","countryName":"Swaziland"},{"countryCode":"SE","countryName":"Sweden"},{"countryCode":"CH","countryName":"Switzerland"},{"countryCode":"SY","countryName":"Syria"},{"countryCode":"TW","countryName":"Taiwan"},{"countryCode":"TJ","countryName":"Tajikistan"},{"countryCode":"TZ","countryName":"Tanzania"},{"countryCode":"TH","countryName":"Thailand"},{"countryCode":"TG","countryName":"Togo"},{"countryCode":"TK","countryName":"Tokelau"},{"countryCode":"TO","countryName":"Tonga"},{"countryCode":"TT","countryName":"Trinidad and Tobago"},{"countryCode":"TN","countryName":"Tunisia"},{"countryCode":"TR","countryName":"Turkey"},{"countryCode":"TM","countryName":"Turkmenistan"},{"countryCode":"TC","countryName":"Turks and Caicos Islands"},{"countryCode":"TV","countryName":"Tuvalu"},{"countryCode":"UM","countryName":"U.S. Minor Outlying Islands"},{"countryCode":"VI","countryName":"U.S. Virgin Islands"},{"countryCode":"UG","countryName":"Uganda"},{"countryCode":"UA","countryName":"Ukraine"},{"countryCode":"AE","countryName":"United Arab Emirates"},{"countryCode":"GB","countryName":"United Kingdom"},{"countryCode":"US","countryName":"United States"},{"countryCode":"UY","countryName":"Uruguay"},{"countryCode":"UZ","countryName":"Uzbekistan"},{"countryCode":"VU","countryName":"Vanuatu"},{"countryCode":"VA","countryName":"Vatican City"},{"countryCode":"VE","countryName":"Venezuela"},{"countryCode":"VN","countryName":"Vietnam"},{"countryCode":"WF","countryName":"Wallis and Futuna"},{"countryCode":"EH","countryName":"Western Sahara"},{"countryCode":"YE","countryName":"Yemen"},{"countryCode":"ZM","countryName":"Zambia"},{"countryCode":"ZW","countryName":"Zimbabwe"}]

def get_country(countryCode):
    country_obj = model.Country.query( model.Country.countryCode == countryCode ).get()

    if not country_obj:
        countryName = None
        for c in countries:
            if c["countryCode"] == countryCode:
                countryName = c["countryName"]
                break

        if countryName:
            country_obj = model.Country( countryName=countryName, countryCode=countryCode )
            country_obj.put()


    return country_obj
def check_countries(country_obj):
    # delete a country if there are no goals associated with the country
    # logging.error(country_obj.key)
    time.sleep(0.3)
    goals_for_country = model.Goal.query(model.Goal.country_key == country_obj.key).get(use_cache=False, use_memcache=False)
    # logging.error("GOALS FRO COUNTRY........")
    # logging.error(country_obj.countryCode)
    # logging.error(goals_for_country)
    if not goals_for_country:
        country_obj.key.delete()

def add_count(count_type):
    count = model.Count.query().get()

    if not count:
        count = model.Count()
        count.put()

    if count_type == "user":
        count.users += 1
        count.put()

def add_goal(user_obj, goal_img_url, goal_title, goal_description):
    logging.error("utils - user_obj")
    logging.error(user_obj)
    goal = model.Goal(user=user_obj.key, image=goal_img_url, title=goal_title, description=goal_description)
    goal.put()
    
    user_obj.total_goals += 1
    user_obj.total_points += goal_points
    user_obj.put()
    
    return goal

def add_victory(user_obj, goal_img_url, goal_title, goal_description):
    goal = model.Goal(user=user_obj.key, image=goal_img_url, title=goal_title, description=goal_description, achieved=True)
    goal.put()
    
    user_obj.total_victories += 1
    user_obj.total_points += victory_points
    user_obj.put()
    
    return goal
    
def set_status(user_obj):
    if user_obj.total_points <=100:
        user_obj.status = "bronze"
    elif user_obj.total_points <=1000 and user_obj.total_points > 100:
        user_obj.status = "silver"
    elif user_obj.total_points > 1000 :
        user_obj.status = "gold"
    
"""
def add_board(user_obj, board_type, board_name, board_description):
    if board_type == "vision":
        new_vision_board = model.VisionBoard( user = user_obj.key, title = board_name, description = board_description )
        new_vision_board.put()
    elif board_type == "victory":
        new_victory_board = model.VictoryBoard( user = user_obj.key, title = board_name, description = board_description )
        new_victory_board.put()
"""

def generate_new_password(email):
    new_pw = ''.join(random.choice(string.ascii_uppercase + string.digits + string.ascii_lowercase) for _ in range(8))
    logging.error("new pw: %s" % new_pw)
    user_obj = model.User.by_email(email)
    
    new_pw_hash = make_pw_hash(user_obj.email, new_pw)
    user_obj.pw_hash = new_pw_hash
    user_obj.put()
    
    mail.send_mail(sender=sender_email,
        to=email,
        subject="New Tempory Password",
        body="Your New Tempory password: %s, please change your password after logging in." % new_pw)

# YOUTUBE VIMEO PARSER FUNCTION
#http://www.youtube.com/embed/VIDEO_ID
def parse_url(url_q):
    parse_url = urlparse(url_q)
    host = parse_url.hostname
    path = parse_url.path
    query = parse_url.query
    return [host, path, query]
        
def youtube_vimeo(src):

    youtube_query = False
    vimeo_path = False
    error = False
    
    host = parse_url(src)[0]
    path = parse_url(src)[1]
    query = parse_url(src)[2]
        
    if host == None:
        host = False
    
    if host:
        #YOUTUBE
        if host == 'youtu.be':
            youtube_query = path[1:]
                
        elif host in ('www.youtube.com', 'youtube.com'):
        # credit: http://stackoverflow.com/questions/4356538/how-can-i-extract-video-id-from-youtubes-link-in-python
            if path == '/watch':
                youtube_query = parse_qs(query)['v'][0]
            elif path[:7] == '/embed/':
                youtube_query = path.split('/')[2]
            elif path[:3] == '/v/':
                youtube_query = path.split('/')[2]
            else:
                error = 'invlaid URL ensure it is a valid Youtube/Vimeo video'
                    
        #VIMEO
        elif 'www.vimeo.com' in host or 'vimeo.com' in host:
            try:
                vimeo_path = int(path[1:])
            except ValueError:
                response = urllib2.urlopen(src)
                vimeo_url_with_id = response.geturl()
                new_vimeo_parse = urlparse(vimeo_url_with_id)
                        
                if new_vimeo_parse.hostname == 'player.vimeo.com':
                    vimeo_path = new_vimeo_parse.path[7:]
                else:
                    vimeo_path = new_vimeo_parse.path[1:]
                    try:
                        vimeo_path = int(path[1:])
                    except ValueError:
                        error = 'vimeo error'
    
    data = {
    'youtube_query':youtube_query,
    'vimeo_path':vimeo_path,
    'error':error
    }
                
    return data
        
def send_mail(email):
    form_fields = {
      "first_name": "Albert",
      "last_name": "Johnson",
      "email_address": "Albert.Johnson@example.com"
    }
    
    url = "https://mandrillapp.com/api/1.0/messages/send.json"
    
    form_json = {
        "key": MANDRILL_KEY,
        "message": {
            "html": "<p>This is to confirm your registration at Bucket Vision<br /> If you didn't sign up at <a href='http://bucketvision.com/'>Bucket Vision</a> please contact us at <a href='mailto:hello@bucketvision.com'>hello@bucketvision.com</a></p>",
            "text": "Welcome to Bucket Vision",
            "subject": "Bucket Vision Confirmation",
            "from_email": "hello@bucketvision.com",
            "from_name": "Bucket Vision Team",
            "to": [
                {
                    "email": email,
                    "name": "New user",
                    "type": "to"
                }
            ],
            "headers": {
                "Reply-To": "hello@bucketvision.com"
            },
            "important": False,
            "track_opens": None,
            "track_clicks": None,
            "auto_text": None,
            "auto_html": None,
            "inline_css": None,
            "url_strip_qs": None,
            "preserve_recipients": None,
            "view_content_link": None,
            "bcc_address": None,
            "tracking_domain": None,
            "signing_domain": None,
            "return_path_domain": None,
            "merge": True,
            "global_merge_vars": [
                {
                    "name": "merge1",
                    "content": "merge1 content"
                }
            ],
            "merge_vars": [
                {
                    "rcpt": "recipient.email@example.com",
                    "vars": [
                        {
                            "name": "merge2",
                            "content": "merge2 content"
                        }
                    ]
                }
            ],
            "tags": [
                "password-resets"
            ],
            "subaccount": None,
            "google_analytics_domains": [
                None
            ],
            "google_analytics_campaign": None,
            "metadata": {
                "website": None
            },
            "recipient_metadata": None,
            "attachments": None,
            "images": None
        },
        "async": False,
        "ip_pool": "Main Pool",
        "send_at": None
    }
    
    #form_data = urllib.urlencode(form_fields)
    result = urlfetch.fetch(url=url, payload=json.dumps(form_json), method=urlfetch.POST)#, #headers={'Content-Type': 'application/x-www-form-urlencoded'})
    #logging.error("!!!!!!!!!!!!!@@@@@@@@@@@@@ EMAIL @@@@@@@@@!!!!!!!!!!!!!!!")
    #logging.error(result)
    
# countries = [
#             {
#                 "countryCode": "AD",
#                 "countryName": "Andorra"
#             },
#             {
#                 "countryCode": "AE",
#                 "countryName": "United Arab Emirates"
#             },
#             {
#                 "countryCode": "AF",
#                 "countryName": "Afghanistan"
#             },
#             {
#                 "countryCode": "AG",
#                 "countryName": "Antigua and Barbuda"
#             },
#             {
#                 "countryCode": "AI",
#                 "countryName": "Anguilla"
#             },
#             {
#                 "countryCode": "AL",
#                 "countryName": "Albania"
#             },
#             {
#                 "countryCode": "AM",
#                 "countryName": "Armenia"
#             },
#             {
#                 "countryCode": "AO",
#                 "countryName": "Angola"
#             },
#             {
#                 "countryCode": "AQ",
#                 "countryName": "Antarctica"
#             },
#             {
#                 "countryCode": "AR",
#                 "countryName": "Argentina"
#             },
#             {
#                 "countryCode": "AS",
#                 "countryName": "American Samoa"
#             },
#             {
#                 "countryCode": "AT",
#                 "countryName": "Austria"
#             },
#             {
#                 "countryCode": "AU",
#                 "countryName": "Australia"
#             },
#             {
#                 "countryCode": "AW",
#                 "countryName": "Aruba"
#             },
#             {
#                 "countryCode": "AX",
#                 "countryName": "Aland"
#             },
#             {
#                 "countryCode": "AZ",
#                 "countryName": "Azerbaijan"
#             },
#             {
#                 "countryCode": "BA",
#                 "countryName": "Bosnia and Herzegovina"
#             },
#             {
#                 "countryCode": "BB",
#                 "countryName": "Barbados"
#             },
#             {
#                 "countryCode": "BD",
#                 "countryName": "Bangladesh"
#             },
#             {
#                 "countryCode": "BE",
#                 "countryName": "Belgium"
#             },
#             {
#                 "countryCode": "BF",
#                 "countryName": "Burkina Faso"
#             },
#             {
#                 "countryCode": "BG",
#                 "countryName": "Bulgaria"
#             },
#             {
#                 "countryCode": "BH",
#                 "countryName": "Bahrain"
#             },
#             {
#                 "countryCode": "BI",
#                 "countryName": "Burundi"
#             },
#             {
#                 "countryCode": "BJ",
#                 "countryName": "Benin"
#             },
#             {
#                 "countryCode": "BL",
#                 "countryName": "Saint Barthelemy"
#             },
#             {
#                 "countryCode": "BM",
#                 "countryName": "Bermuda"
#             },
#             {
#                 "countryCode": "BN",
#                 "countryName": "Brunei"
#             },
#             {
#                 "countryCode": "BO",
#                 "countryName": "Bolivia"
#             },
#             {
#                 "countryCode": "BQ",
#                 "countryName": "Bonaire"
#             },
#             {
#                 "countryCode": "BR",
#                 "countryName": "Brazil"
#             },
#             {
#                 "countryCode": "BS",
#                 "countryName": "Bahamas"
#             },
#             {
#                 "countryCode": "BT",
#                 "countryName": "Bhutan"
#             },
#             {
#                 "countryCode": "BV",
#                 "countryName": "Bouvet Island"
#             },
#             {
#                 "countryCode": "BW",
#                 "countryName": "Botswana"
#             },
#             {
#                 "countryCode": "BY",
#                 "countryName": "Belarus"
#             },
#             {
#                 "countryCode": "BZ",
#                 "countryName": "Belize"
#             },
#             {
#                 "countryCode": "CA",
#                 "countryName": "Canada"
#             },
#             {
#                 "countryCode": "CC",
#                 "countryName": "Cocos [Keeling] Islands"
#             },
#             {
#                 "countryCode": "CD",
#                 "countryName": "Democratic Republic of the Congo"
#             },
#             {
#                 "countryCode": "CF",
#                 "countryName": "Central African Republic"
#             },
#             {
#                 "countryCode": "CG",
#                 "countryName": "Republic of the Congo"
#             },
#             {
#                 "countryCode": "CH",
#                 "countryName": "Switzerland"
#             },
#             {
#                 "countryCode": "CI",
#                 "countryName": "Ivory Coast"
#             },
#             {
#                 "countryCode": "CK",
#                 "countryName": "Cook Islands"
#             },
#             {
#                 "countryCode": "CL",
#                 "countryName": "Chile"
#             },
#             {
#                 "countryCode": "CM",
#                 "countryName": "Cameroon"
#             },
#             {
#                 "countryCode": "CN",
#                 "countryName": "China"
#             },
#             {
#                 "countryCode": "CO",
#                 "countryName": "Colombia"
#             },
#             {
#                 "countryCode": "CR",
#                 "countryName": "Costa Rica"
#             },
#             {
#                 "countryCode": "CU",
#                 "countryName": "Cuba"
#             },
#             {
#                 "countryCode": "CV",
#                 "countryName": "Cape Verde"
#             },
#             {
#                 "countryCode": "CW",
#                 "countryName": "Curacao"
#             },
#             {
#                 "countryCode": "CX",
#                 "countryName": "Christmas Island"
#             },
#             {
#                 "countryCode": "CY",
#                 "countryName": "Cyprus"
#             },
#             {
#                 "countryCode": "CZ",
#                 "countryName": "Czech Republic"
#             },
#             {
#                 "countryCode": "DE",
#                 "countryName": "Germany"
#             },
#             {
#                 "countryCode": "DJ",
#                 "countryName": "Djibouti"
#             },
#             {
#                 "countryCode": "DK",
#                 "countryName": "Denmark"
#             },
#             {
#                 "countryCode": "DM",
#                 "countryName": "Dominica"
#             },
#             {
#                 "countryCode": "DO",
#                 "countryName": "Dominican Republic"
#             },
#             {
#                 "countryCode": "DZ",
#                 "countryName": "Algeria"
#             },
#             {
#                 "countryCode": "EC",
#                 "countryName": "Ecuador"
#             },
#             {
#                 "countryCode": "EE",
#                 "countryName": "Estonia"
#             },
#             {
#                 "countryCode": "EG",
#                 "countryName": "Egypt"
#             },
#             {
#                 "countryCode": "EH",
#                 "countryName": "Western Sahara"
#             },
#             {
#                 "countryCode": "ER",
#                 "countryName": "Eritrea"
#             },
#             {
#                 "countryCode": "ES",
#                 "countryName": "Spain"
#             },
#             {
#                 "countryCode": "ET",
#                 "countryName": "Ethiopia"
#             },
#             {
#                 "countryCode": "FI",
#                 "countryName": "Finland"
#             },
#             {
#                 "countryCode": "FJ",
#                 "countryName": "Fiji"
#             },
#             {
#                 "countryCode": "FK",
#                 "countryName": "Falkland Islands"
#             },
#             {
#                 "countryCode": "FM",
#                 "countryName": "Micronesia"
#             },
#             {
#                 "countryCode": "FO",
#                 "countryName": "Faroe Islands"
#             },
#             {
#                 "countryCode": "FR",
#                 "countryName": "France"
#             },
#             {
#                 "countryCode": "GA",
#                 "countryName": "Gabon"
#             },
#             {
#                 "countryCode": "GB",
#                 "countryName": "United Kingdom"
#             },
#             {
#                 "countryCode": "GD",
#                 "countryName": "Grenada"
#             },
#             {
#                 "countryCode": "GE",
#                 "countryName": "Georgia"
#             },
#             {
#                 "countryCode": "GF",
#                 "countryName": "French Guiana"
#             },
#             {
#                 "countryCode": "GG",
#                 "countryName": "Guernsey"
#             },
#             {
#                 "countryCode": "GH",
#                 "countryName": "Ghana"
#             },
#             {
#                 "countryCode": "GI",
#                 "countryName": "Gibraltar"
#             },
#             {
#                 "countryCode": "GL",
#                 "countryName": "Greenland"
#             },
#             {
#                 "countryCode": "GM",
#                 "countryName": "Gambia"
#             },
#             {
#                 "countryCode": "GN",
#                 "countryName": "Guinea"
#             },
#             {
#                 "countryCode": "GP",
#                 "countryName": "Guadeloupe"
#             },
#             {
#                 "countryCode": "GQ",
#                 "countryName": "Equatorial Guinea"
#             },
#             {
#                 "countryCode": "GR",
#                 "countryName": "Greece"
#             },
#             {
#                 "countryCode": "GS",
#                 "countryName": "South Georgia and the South Sandwich Islands"
#             },
#             {
#                 "countryCode": "GT",
#                 "countryName": "Guatemala"
#             },
#             {
#                 "countryCode": "GU",
#                 "countryName": "Guam"
#             },
#             {
#                 "countryCode": "GW",
#                 "countryName": "Guinea-Bissau"
#             },
#             {
#                 "countryCode": "GY",
#                 "countryName": "Guyana"
#             },
#             {
#                 "countryCode": "HK",
#                 "countryName": "Hong Kong"
#             },
#             {
#                 "countryCode": "HM",
#                 "countryName": "Heard Island and McDonald Islands"
#             },
#             {
#                 "countryCode": "HN",
#                 "countryName": "Honduras"
#             },
#             {
#                 "countryCode": "HR",
#                 "countryName": "Croatia"
#             },
#             {
#                 "countryCode": "HT",
#                 "countryName": "Haiti"
#             },
#             {
#                 "countryCode": "HU",
#                 "countryName": "Hungary"
#             },
#             {
#                 "countryCode": "ID",
#                 "countryName": "Indonesia"
#             },
#             {
#                 "countryCode": "IE",
#                 "countryName": "Ireland"
#             },
#             {
#                 "countryCode": "IL",
#                 "countryName": "Israel"
#             },
#             {
#                 "countryCode": "IM",
#                 "countryName": "Isle of Man"
#             },
#             {
#                 "countryCode": "IN",
#                 "countryName": "India"
#             },
#             {
#                 "countryCode": "IO",
#                 "countryName": "British Indian Ocean Territory"
#             },
#             {
#                 "countryCode": "IQ",
#                 "countryName": "Iraq"
#             },
#             {
#                 "countryCode": "IR",
#                 "countryName": "Iran"
#             },
#             {
#                 "countryCode": "IS",
#                 "countryName": "Iceland"
#             },
#             {
#                 "countryCode": "IT",
#                 "countryName": "Italy"
#             },
#             {
#                 "countryCode": "JE",
#                 "countryName": "Jersey"
#             },
#             {
#                 "countryCode": "JM",
#                 "countryName": "Jamaica"
#             },
#             {
#                 "countryCode": "JO",
#                 "countryName": "Jordan"
#             },
#             {
#                 "countryCode": "JP",
#                 "countryName": "Japan"
#             },
#             {
#                 "countryCode": "KE",
#                 "countryName": "Kenya"
#             },
#             {
#                 "countryCode": "KG",
#                 "countryName": "Kyrgyzstan"
#             },
#             {
#                 "countryCode": "KH",
#                 "countryName": "Cambodia"
#             },
#             {
#                 "countryCode": "KI",
#                 "countryName": "Kiribati"
#             },
#             {
#                 "countryCode": "KM",
#                 "countryName": "Comoros"
#             },
#             {
#                 "countryCode": "KN",
#                 "countryName": "Saint Kitts and Nevis"
#             },
#             {
#                 "countryCode": "KP",
#                 "countryName": "North Korea"
#             },
#             {
#                 "countryCode": "KR",
#                 "countryName": "South Korea"
#             },
#             {
#                 "countryCode": "KW",
#                 "countryName": "Kuwait"
#             },
#             {
#                 "countryCode": "KY",
#                 "countryName": "Cayman Islands"
#             },
#             {
#                 "countryCode": "KZ",
#                 "countryName": "Kazakhstan"
#             },
#             {
#                 "countryCode": "LA",
#                 "countryName": "Laos"
#             },
#             {
#                 "countryCode": "LB",
#                 "countryName": "Lebanon"
#             },
#             {
#                 "countryCode": "LC",
#                 "countryName": "Saint Lucia"
#             },
#             {
#                 "countryCode": "LI",
#                 "countryName": "Liechtenstein"
#             },
#             {
#                 "countryCode": "LK",
#                 "countryName": "Sri Lanka"
#             },
#             {
#                 "countryCode": "LR",
#                 "countryName": "Liberia"
#             },
#             {
#                 "countryCode": "LS",
#                 "countryName": "Lesotho"
#             },
#             {
#                 "countryCode": "LT",
#                 "countryName": "Lithuania"
#             },
#             {
#                 "countryCode": "LU",
#                 "countryName": "Luxembourg"
#             },
#             {
#                 "countryCode": "LV",
#                 "countryName": "Latvia"
#             },
#             {
#                 "countryCode": "LY",
#                 "countryName": "Libya"
#             },
#             {
#                 "countryCode": "MA",
#                 "countryName": "Morocco"
#             },
#             {
#                 "countryCode": "MC",
#                 "countryName": "Monaco"
#             },
#             {
#                 "countryCode": "MD",
#                 "countryName": "Moldova"
#             },
#             {
#                 "countryCode": "ME",
#                 "countryName": "Montenegro"
#             },
#             {
#                 "countryCode": "MF",
#                 "countryName": "Saint Martin"
#             },
#             {
#                 "countryCode": "MG",
#                 "countryName": "Madagascar"
#             },
#             {
#                 "countryCode": "MH",
#                 "countryName": "Marshall Islands"
#             },
#             {
#                 "countryCode": "MK",
#                 "countryName": "Macedonia"
#             },
#             {
#                 "countryCode": "ML",
#                 "countryName": "Mali"
#             },
#             {
#                 "countryCode": "MM",
#                 "countryName": "Myanmar [Burma]"
#             },
#             {
#                 "countryCode": "MN",
#                 "countryName": "Mongolia"
#             },
#             {
#                 "countryCode": "MO",
#                 "countryName": "Macao"
#             },
#             {
#                 "countryCode": "MP",
#                 "countryName": "Northern Mariana Islands"
#             },
#             {
#                 "countryCode": "MQ",
#                 "countryName": "Martinique"
#             },
#             {
#                 "countryCode": "MR",
#                 "countryName": "Mauritania"
#             },
#             {
#                 "countryCode": "MS",
#                 "countryName": "Montserrat"
#             },
#             {
#                 "countryCode": "MT",
#                 "countryName": "Malta"
#             },
#             {
#                 "countryCode": "MU",
#                 "countryName": "Mauritius"
#             },
#             {
#                 "countryCode": "MV",
#                 "countryName": "Maldives"
#             },
#             {
#                 "countryCode": "MW",
#                 "countryName": "Malawi"
#             },
#             {
#                 "countryCode": "MX",
#                 "countryName": "Mexico"
#             },
#             {
#                 "countryCode": "MY",
#                 "countryName": "Malaysia"
#             },
#             {
#                 "countryCode": "MZ",
#                 "countryName": "Mozambique"
#             },
#             {
#                 "countryCode": "NA",
#                 "countryName": "Namibia"
#             },
#             {
#                 "countryCode": "NC",
#                 "countryName": "New Caledonia"
#             },
#             {
#                 "countryCode": "NE",
#                 "countryName": "Niger"
#             },
#             {
#                 "countryCode": "NF",
#                 "countryName": "Norfolk Island"
#             },
#             {
#                 "countryCode": "NG",
#                 "countryName": "Nigeria"
#             },
#             {
#                 "countryCode": "NI",
#                 "countryName": "Nicaragua"
#             },
#             {
#                 "countryCode": "NL",
#                 "countryName": "Netherlands"
#             },
#             {
#                 "countryCode": "NO",
#                 "countryName": "Norway"
#             },
#             {
#                 "countryCode": "NP",
#                 "countryName": "Nepal"
#             },
#             {
#                 "countryCode": "NR",
#                 "countryName": "Nauru"
#             },
#             {
#                 "countryCode": "NU",
#                 "countryName": "Niue"
#             },
#             {
#                 "countryCode": "NZ",
#                 "countryName": "New Zealand"
#             },
#             {
#                 "countryCode": "OM",
#                 "countryName": "Oman"
#             },
#             {
#                 "countryCode": "PA",
#                 "countryName": "Panama"
#             },
#             {
#                 "countryCode": "PE",
#                 "countryName": "Peru"
#             },
#             {
#                 "countryCode": "PF",
#                 "countryName": "French Polynesia"
#             },
#             {
#                 "countryCode": "PG",
#                 "countryName": "Papua New Guinea"
#             },
#             {
#                 "countryCode": "PH",
#                 "countryName": "Philippines"
#             },
#             {
#                 "countryCode": "PK",
#                 "countryName": "Pakistan"
#             },
#             {
#                 "countryCode": "PL",
#                 "countryName": "Poland"
#             },
#             {
#                 "countryCode": "PM",
#                 "countryName": "Saint Pierre and Miquelon"
#             },
#             {
#                 "countryCode": "PN",
#                 "countryName": "Pitcairn Islands"
#             },
#             {
#                 "countryCode": "PR",
#                 "countryName": "Puerto Rico"
#             },
#             {
#                 "countryCode": "PS",
#                 "countryName": "Palestine"
#             },
#             {
#                 "countryCode": "PT",
#                 "countryName": "Portugal"
#             },
#             {
#                 "countryCode": "PW",
#                 "countryName": "Palau"
#             },
#             {
#                 "countryCode": "PY",
#                 "countryName": "Paraguay"
#             },
#             {
#                 "countryCode": "QA",
#                 "countryName": "Qatar"
#             },
#             {
#                 "countryCode": "RE",
#                 "countryName": "Reunion"
#             },
#             {
#                 "countryCode": "RO",
#                 "countryName": "Romania"
#             },
#             {
#                 "countryCode": "RS",
#                 "countryName": "Serbia"
#             },
#             {
#                 "countryCode": "RU",
#                 "countryName": "Russia"
#             },
#             {
#                 "countryCode": "RW",
#                 "countryName": "Rwanda"
#             },
#             {
#                 "countryCode": "SA",
#                 "countryName": "Saudi Arabia"
#             },
#             {
#                 "countryCode": "SB",
#                 "countryName": "Solomon Islands"
#             },
#             {
#                 "countryCode": "SC",
#                 "countryName": "Seychelles"
#             },
#             {
#                 "countryCode": "SD",
#                 "countryName": "Sudan"
#             },
#             {
#                 "countryCode": "SE",
#                 "countryName": "Sweden"
#             },
#             {
#                 "countryCode": "SG",
#                 "countryName": "Singapore"
#             },
#             {
#                 "countryCode": "SH",
#                 "countryName": "Saint Helena"
#             },
#             {
#                 "countryCode": "SI",
#                 "countryName": "Slovenia"
#             },
#             {
#                 "countryCode": "SJ",
#                 "countryName": "Svalbard and Jan Mayen"
#             },
#             {
#                 "countryCode": "SK",
#                 "countryName": "Slovakia"
#             },
#             {
#                 "countryCode": "SL",
#                 "countryName": "Sierra Leone"
#             },
#             {
#                 "countryCode": "SM",
#                 "countryName": "San Marino"
#             },
#             {
#                 "countryCode": "SN",
#                 "countryName": "Senegal"
#             },
#             {
#                 "countryCode": "SO",
#                 "countryName": "Somalia"
#             },
#             {
#                 "countryCode": "SR",
#                 "countryName": "Suriname"
#             },
#             {
#                 "countryCode": "SS",
#                 "countryName": "South Sudan"
#             },
#             {
#                 "countryCode": "ST",
#                 "countryName": "Sao Tome and Principe"
#             },
#             {
#                 "countryCode": "SV",
#                 "countryName": "El Salvador"
#             },
#             {
#                 "countryCode": "SX",
#                 "countryName": "Sint Maarten"
#             },
#             {
#                 "countryCode": "SY",
#                 "countryName": "Syria"
#             },
#             {
#                 "countryCode": "SZ",
#                 "countryName": "Swaziland"
#             },
#             {
#                 "countryCode": "TC",
#                 "countryName": "Turks and Caicos Islands"
#             },
#             {
#                 "countryCode": "TD",
#                 "countryName": "Chad"
#             },
#             {
#                 "countryCode": "TF",
#                 "countryName": "French Southern Territories"
#             },
#             {
#                 "countryCode": "TG",
#                 "countryName": "Togo"
#             },
#             {
#                 "countryCode": "TH",
#                 "countryName": "Thailand"
#             },
#             {
#                 "countryCode": "TJ",
#                 "countryName": "Tajikistan"
#             },
#             {
#                 "countryCode": "TK",
#                 "countryName": "Tokelau"
#             },
#             {
#                 "countryCode": "TL",
#                 "countryName": "East Timor"
#             },
#             {
#                 "countryCode": "TM",
#                 "countryName": "Turkmenistan"
#             },
#             {
#                 "countryCode": "TN",
#                 "countryName": "Tunisia"
#             },
#             {
#                 "countryCode": "TO",
#                 "countryName": "Tonga"
#             },
#             {
#                 "countryCode": "TR",
#                 "countryName": "Turkey"
#             },
#             {
#                 "countryCode": "TT",
#                 "countryName": "Trinidad and Tobago"
#             },
#             {
#                 "countryCode": "TV",
#                 "countryName": "Tuvalu"
#             },
#             {
#                 "countryCode": "TW",
#                 "countryName": "Taiwan"
#             },
#             {
#                 "countryCode": "TZ",
#                 "countryName": "Tanzania"
#             },
#             {
#                 "countryCode": "UA",
#                 "countryName": "Ukraine"
#             },
#             {
#                 "countryCode": "UG",
#                 "countryName": "Uganda"
#             },
#             {
#                 "countryCode": "UM",
#                 "countryName": "U.S. Minor Outlying Islands"
#             },
#             {
#                 "countryCode": "US",
#                 "countryName": "United States"
#             },
#             {
#                 "countryCode": "UY",
#                 "countryName": "Uruguay"
#             },
#             {
#                 "countryCode": "UZ",
#                 "countryName": "Uzbekistan"
#             },
#             {
#                 "countryCode": "VA",
#                 "countryName": "Vatican City"
#             },
#             {
#                 "countryCode": "VC",
#                 "countryName": "Saint Vincent and the Grenadines"
#             },
#             {
#                 "countryCode": "VE",
#                 "countryName": "Venezuela"
#             },
#             {
#                 "countryCode": "VG",
#                 "countryName": "British Virgin Islands"
#             },
#             {
#                 "countryCode": "VI",
#                 "countryName": "U.S. Virgin Islands"
#             },
#             {
#                 "countryCode": "VN",
#                 "countryName": "Vietnam"
#             },
#             {
#                 "countryCode": "VU",
#                 "countryName": "Vanuatu"
#             },
#             {
#                 "countryCode": "WF",
#                 "countryName": "Wallis and Futuna"
#             },
#             {
#                 "countryCode": "WS",
#                 "countryName": "Samoa"
#             },
#             {
#                 "countryCode": "XK",
#                 "countryName": "Kosovo"
#             },
#             {
#                 "countryCode": "YE",
#                 "countryName": "Yemen"
#             },
#             {
#                 "countryCode": "YT",
#                 "countryName": "Mayotte"
#             },
#             {
#                 "countryCode": "ZA",
#                 "countryName": "South Africa"
#             },
#             {
#                 "countryCode": "ZM",
#                 "countryName": "Zambia"
#             },
#             {
#                 "countryCode": "ZW",
#                 "countryName": "Zimbabwe"
#             }
#         ]
    
    
    
    
    