from flask import Flask, escape, url_for, request, render_template, redirect, session, g
# from flask_mysqldb import MySQL
#from flask_login import LoginManager
import time
from pytz import timezone
import random
import string
import hashlib
import cv2
import os
from werkzeug.utils import secure_filename
import logging
import pymysql
import pyrebase
import datetime
import html
import uuid
import gunicorn
import secrets
import operator
# import random

import requests
import json

import PIL
from PIL import Image
# import html2text


##################################################### FIREBASE CONFIG ########################################################
config = {
    "apiKey": "AIzaSyAhnooN0Dbe3Te51qX1ckPhk5ZFvedu6R0",
    "authDomain": "getlex-5b86d.firebaseapp.com",
    "databaseURL": "https://getlex-5b86d.firebaseio.com",
    "projectId": "getlex-5b86d",
    "storageBucket": "getlex-5b86d.appspot.com",
    "messagingSenderId": "1088823644810",
    "appId": "1:1088823644810:web:9fdda22076b6f699221373"}
firebase = pyrebase.initialize_app(config)
db = firebase.database()
storage = firebase.storage()
auth = firebase.auth()


####################################################### FLASK CONFIG #########################################################
app = Flask(__name__,template_folder='templates',static_folder='static')
user = ''
key = secrets.token_urlsafe(16)
app.config['SECRET_KEY'] = key
UPLOAD_FOLDER = '/tmp/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


####################################################### FUNCTIONS ############################################################
tz = timezone('EST')

def dash_to_slash(date):
    return("/".join(date.split('-')))

def get_date_title(date):
    num = get_date_num(date)
    week_days = ['Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday','Monday']*53
    return week_days[num]

def get_date_num(date):
    months_ = [31,28,31,30,31,30,31,31,30,31,30,31]
    d_month = int(date.split('-')[0])-1
    d_day = int(date.split('-')[1])
    days = sum(months_[0:d_month])+d_day
    return(days)

def cur_date():
    date = str(datetime.datetime.now(tz)).split(" ")[0]
    date = date.split('-')
    date = date[1]+'-'+date[2]+'-'+date[0]
    return(date)

FIRST = ''
LAST = ''


########################################################## LOGIN #############################################################
@app.route('/login',methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        global img_url
        global FIRST
        global LAST
        email = request.form.get('email',None)
        password = request.form.get('password',None)
        
        try:
            user = auth.sign_in_with_email_and_password(email,password)
            session['id'] = auth.get_account_info(user['idToken'])['users'][0]['localId']
            img_url = db.child(session['id']).child('p_pic').get().val()
            FIRST = db.child(session['id']).child('first').get().val()
            LAST = db.child(session['id']).child('last').get().val()
            return redirect(url_for('write',user=session['id']))
        except:
            return render_template('login.html',msg='Incorrect account information.')
            
    return render_template('login.html')


#################################################### CREATE AN ACCCOUNT ######################################################
@app.route('/create',methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        global img_url
        global FIRST
        global LAST
        email = request.form.get('email',None)
        password = request.form.get('password',None)
        first = request.form.get('first',None)
        last = request.form.get('last',None)
        
        try:
            user = auth.create_user_with_email_and_password(email,password)
            session['id'] = auth.get_account_info(user['idToken'])['users'][0]['localId']
        except:
            return render_template('signup.html',msg='That account already exists.')
        
        img = request.files["img"]
        img.save(os.path.join(app.config["UPLOAD_FOLDER"], img.filename))
        img_path = os.path.join(app.config["UPLOAD_FOLDER"], img.filename)
        
        basewidth = 200
        img = Image.open(img_path)
        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
        img.save(img_path)
        
        storage.child("profile/"+session['id']).put(img_path)
        img = storage.child("profile/"+session['id']).get_url(img_path)
        img_url = img
        FIRST = first
        LAST = last
        DATE = cur_date()
        text = "<p><b>Hi :)</b></p><div><br></div><div>Welcome to <i>Lex</i> - a productivity platform for daily updates.</div><div><br></div><div>Click <a href=\"{{ url_for('write',user='{}') }}\"><b>here</b></a> to send your first update!</div><p></p>".format(session['id'])
        
        try:
            num = len([i for i in db.child('JJ5TaGwnn5cbRzfTdP04S5gPj8y1').child('followers').get().val()])
        except:
            num = 0
        db.child('JJ5TaGwnn5cbRzfTdP04S5gPj8y1').update({num:session['id']})
        db.child(session['id']).update({'email':email,'following':{'JJ5TaGwnn5cbRzfTdP04S5gPj8y1':DATE},'received':{'JJ5TaGwnn5cbRzfTdP04S5gPj8y1':{DATE:text}}, 'password':password, 'first':first, 'last':last, 'p_pic':img,'follower-count':0,'sent':0, 'following-count':1})        
        return redirect(url_for('choose_integrate',user=session['id']))
    
    return render_template('signup.html')


##################################################### INTEGRATE SLACK ######################################################
@app.route('/integrate/<user>',methods=['GET', 'POST'])
def choose_integrate(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/integrate_slack.html', user=user)



@app.route('/step1/<user>',methods=['GET', 'POST'])
def step1(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    if request.method == 'POST':
        return redirect(url_for('step2',user=user))
    
    return render_template('integrate/step-1.html', user=user)



@app.route('/step2/<user>',methods=['GET', 'POST'])
def step2(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-2.html', user=user)


@app.route('/step3-loggedout/<user>',methods=['GET', 'POST'])
def step3loggedout(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    if request.method == 'POST':
        return redirect(url_for('step4',user=user))
    
    return render_template('integrate/step-3-notlogged.html', user=user)



@app.route('/step4/<user>',methods=['GET', 'POST'])
def step4(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-4.html', user=user)



@app.route('/step5/<user>',methods=['GET', 'POST'])
def step5(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-5.html', user=user)



@app.route('/step6/<user>',methods=['GET', 'POST'])
def step6(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-6.html', user=user)



@app.route('/step7/<user>',methods=['GET', 'POST'])
def step7(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-7.html', user=user)



@app.route('/step8/<user>',methods=['GET', 'POST'])
def step8(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-8.html', user=user)



@app.route('/step9/<user>',methods=['GET', 'POST'])
def step9(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    return render_template('integrate/step-9.html', user=user)



@app.route('/addslackmembers/<user>',methods=['GET', 'POST'])
def add_slack_members(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    if request.method == 'POST':
        channel = request.form.get('channel',None)
        url = request.form.get('url',None)
        remove = request.form.get('remove',None)
                
        if remove != "":
            db.child(user).child('slack').child(remove).remove()
        
        else:
            db.child(user).child('slack').update({channel:url})
        
    tmp = db.child(user).child('slack').get().val()
    end = ""
    if tmp != None:
        channels = [i for i in tmp]
        for i in channels:
            end += """<div id="friend" style="float: left;padding-right: 10px;width: 160px;"><img  src="https://firebasestorage.googleapis.com/v0/b/getlex-5b86d.appspot.com/o/integrate%2Ffiller_profile_pic.jpg?alt=media&token=2c07e46e-1b56-42a5-8ee4-fa45c923a7b4" style="object-fit: cover;width: 30px;height: 30px;line-height: 30px;cursor: pointer;border-radius: 5px;display: inline-block;"><p style="font-family: Lato, sans-serif;vertical-align: middle;display: inline-block;margin-top: 15px;margin-left: 10px;"><strong>{}</strong></p><p style="font-family: Lato, sans-serif;vertical-align: middle;display: inline-block;margin-top: 15px;margin-left: 10px;"></p><i id="{}" onclick="removeChannel(event)" class="la la-remove" style="cursor: pointer;float: right;margin: 0 auto;display: block;margin-top: 15px;"></i></div>""".format(i,i)

    return render_template('integrate/add_slack_channels.html', user=user,channel_list=end)



@app.route('/follow_people/<user>',methods=['GET', 'POST'])
def follow_people(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
        
    
    if request.method == 'POST':
        userid = request.form.get('userid',None)
        search = request.form.get('search',None)

        if userid != None:
            db.child(userid).child('requests').update({user:cur_date()})
            db.child(user).child('requested').update({userid:cur_date()})
            return redirect(url_for('follow_people',user=user))

        if search != None:
            search = search.lower()
            
            final = []
            names = []
            for i in db.get().val():
                if i != user:
                    first = db.child(i).child('first').get().val().lower()
                    last = db.child(i).child('last').get().val().lower()
                    name = first+" "+last
                    if search in name:
                        final += [i]
                        names += [name]
            
            try:
                following = [i for i in db.child(user).child('following').get().val()]
                following = "".join(following)
            except:
                following = ""
            try:
                requested = [i for i in db.child(user).child('requested').get().val()]
                requested = "".join(requested)
            except:
                requested = ""
                        
            end = ""
            if len(final) > 0:
                for i in range(len(final)):
                    fullid_ = f'fullid_{i}'
                    halfid_ = f'halfid_{i}'
                    quarterid_ = f'quarterid_{i}'
                    userid_ = f'userid_{i}'
                    img_link1 = db.child(final[i]).child('p_pic').get().val()
                    
                    follow = "Follow"
                    color = "#03a87c"
                    onclick = 'onclick="followUser(event)" id="yeet-9"'
                    text_col = "white"
                    cursor = "pointer"
                    if final[i] in following:
                        follow = "Following"
                        color = "white"
                        text_col = "black"
                        onclick = ''
                        cursor = "not-allowed"
                    elif final[i] in requested:
                        follow = "Requested"
                        color = "white"
                        text_col = "black"
                        onclick = ''
                        cursor = "not-allowed"
                        
                    end += """<form method="post" id="{}"><div id="{}" style="padding-top: 10px;padding-bottom: 10px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 40px;height: 40px;line-height: 30px;border-radius: 5px;"></div><div id="{}" style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p {} style="height: 20px;border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color:{};color: {};border: 1px solid #03a87c;border-radius: 5px 5px 5px 5px;font-size: 11px;cursor: {};display: inline-block;margin-top: 4px;">{}</p><input value="{}" name="userid" style="display:none"></p></div></div></form>""".format(fullid_,halfid_,img_link1,quarterid_,names[i],onclick,color,text_col,cursor,follow,final[i])                    
            
            if end == "":
                return render_template('add_friends_onboard.html',user=user,msg="0 results found.")
            
            return render_template('add_friends_onboard.html',user=user,search_users=end)
        
        
    final = []
    names = []
    for i in db.get().val():
        if i != user:
            first = db.child(i).child('first').get().val().lower()
            last = db.child(i).child('last').get().val().lower()
            name = first+" "+last
            final += [i]
            names += [name]

    try:
        following = [i for i in db.child(user).child('following').get().val()]
        following = "".join(following)
    except:
        following = ""
    try:
        requested = [i for i in db.child(user).child('requested').get().val()]
        requested = "".join(requested)
    except:
        requested = ""

    end = ""
    if len(final) > 0:
        for i in range(len(final)):
            fullid_ = f'fullid_{i}'
            halfid_ = f'halfid_{i}'
            quarterid_ = f'quarterid_{i}'
            userid_ = f'userid_{i}'
            img_link1 = db.child(final[i]).child('p_pic').get().val()

            follow = "Follow"
            color = "#03a87c"
            onclick = 'onclick="followUser(event)" id="yeet-9"'
            text_col = "white"
            cursor = "pointer"
            if final[i] in following:
                follow = "Following"
                color = "white"
                text_col = "black"
                onclick = ''
                cursor = "not-allowed"
            elif final[i] in requested:
                follow = "Requested"
                color = "white"
                text_col = "black"
                onclick = ''
                cursor = "not-allowed"

            end += """<form method="post" id="{}"><div id="{}" style="padding-top: 10px;padding-bottom: 10px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 40px;height: 40px;line-height: 30px;border-radius: 5px;"></div><div id="{}" style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p {} style="height: 20px;border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color:{};color: {};border: 1px solid #03a87c;border-radius: 5px 5px 5px 5px;font-size: 11px;cursor: {};display: inline-block;margin-top: 4px;">{}</p><input value="{}" name="userid" style="display:none"></p></div></div></form>""".format(fullid_,halfid_,img_link1,quarterid_,names[i],onclick,color,text_col,cursor,follow,final[i])   
                    
    
    return render_template('add_friends_onboard.html', user=user,search_users=end)















################################################### NOT LOGGED IN REDIRECT ##################################################
@app.route('/loggedout',methods=['GET', 'POST'])
def not_logged_in():
    return render_template('not_logged_in.html')



def cleanText(text):
    try:
        for i in re.findall('<p.*?>',text,re.DOTALL):
            text = "".join(text.split(i))
    except:
        pass

    try:
        for i in re.findall('<span.*?>',text,re.DOTALL):
            text = "".join(text.split(i))
    except:
        pass
    
    try:
        for i in re.findall('<a.*?>',text,re.DOTALL):
            text = "".join(text.split(i))
    except:
        pass
    
    try:
        for i in re.findall('<b.*?>',text,re.DOTALL):
            text = "*".join(text.split(i))
    except:
        pass

    try:
        for i in re.findall('<div.*?>',text,re.DOTALL):
            text = "".join(text.split(i))
    except:
        pass


    text = text.replace('<br></b>','*\n')
    text = text.replace('<p>','')
    text = text.replace('</p>','')
    text = text.replace('</b>','*')
    text = text.replace('<span>','')
    text = text.replace('</span>','')
    text = text.replace('<div>','')
    text = text.replace('</div>','\n')
    text = text.replace('<br>','')
    text = text.replace('<b>','*')
    text = text.replace('</a>','')
    text = text.replace('</span','')
    text = text.replace('&nbsp;',' ')
    
    return text


################################################# CHOOSE UPDATE RECIPIENTS ###################################################
@app.route('/choose/<user>',methods=['GET', 'POST'])
def choose_send(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    if request.method == 'POST':
        text1 = request.form.get('finallist',None)
        slacklist = request.form.get('slacklist',None)
        
        if slacklist != "":
            text = db.child(user).child('tmp-text').get().val()
            text = cleanText(text)
            msg = {'text':text}
            tmp = slacklist.split("|||")
            
            for i in tmp:
                if len(i) > 0:
                    requests.post(i,data=json.dumps(msg))

        ids = text1.split(' ')
        out = []
        for i in ids:
            if len(i) > 0:
                out += [i]
        
        date = cur_date()
        text_ = db.child(user).child('tmp-text').get().val()
        
        for i in out:
            if i == "click1":
                continue
            db.child(i).child('received').child(user).update({date:text_})
        
        num = db.child(user).child('sent').get().val()
        db.child(user).update({'sent':num+1})
        
        db.child(user).child('updates').child('days').update({date:{'text':text_,'downvotes':{'num':0,'users':'none'},'upvotes':{'num':0,'users':'none'}}})
            
        return redirect(url_for('success',user=user))
           
    integrate = ""
    slacklist = ""
    slack_final = ""
    try:
        slacklist = []
        slack_names = [i for i in db.child(user).child('slack').get().val()]
        for i in slack_names:
            slacklist += [db.child(user).child('slack').child(i).get().val()]
        slacklist = "|||".join(slacklist)
        URLs = []
        for i in slack_names:
            id_tmp1 = secrets.token_urlsafe(16)
            id_tmp2 = secrets.token_urlsafe(16)
            slack_final += """<div class="friend" id="{}" style="margin-top:5px;margin-bbottom:5px;border-radius:5px 5px 5px 5px;float: left;padding-right: 10px;width: 200px;"><img src="https://firebasestorage.googleapis.com/v0/b/getlex-5b86d.appspot.com/o/integrate%2Ffiller_profile_pic.jpg?alt=media&token=2c07e46e-1b56-42a5-8ee4-fa45c923a7b4" style="object-fit: cover;margin-left:5px;width: 30px;height: 30px;line-height: 30px;cursor: pointer;border-radius: 5px;display: inline-block;"><p style="font-family: Lato, sans-serif;vertical-align: middle;display: inline-block;margin-top: 15px;margin-left: 10px;"><strong>{}</strong></p><p style="font-family: Lato, sans-serif;vertical-align: middle;display: inline-block;margin-top: 15px;margin-left: 10px;"></p><i id="{}" onclick="onOffSlack(event)" class="fa fa-toggle-on" style="float:right;cursor:pointer;color: #03a87c;font-size: 35px;margin-bottom: 5px;vertical-align: top;margin-top: 5px;"></i></div>""".format(id_tmp1,i,db.child(user).child('slack').child(i).get().val())
    except:
        integrate = "true"
        
    try:
        f_id = [i for i in db.child(user).child('followers').get().val()]
        finallist = ""
        for i in f_id:
            first = db.child(i).child('first').get().val()
            last = db.child(i).child('last').get().val()
            name = first+" "+last
            img_link = db.child(i).child('p_pic').get().val()
            
            finallist += """<div class="friend" style="width:250px;margin-top: 10px;margin-bottom: 10px;padding-top:10px;padding-bottom:10px;padding-left:5px;border-radius:8px 8px 8px 8px"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 50px;height: 50px;line-height: 30px;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;margin-top: 3px;"><strong>{}</strong></p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Reply rate:</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Upvote rate:</p></div><div style="display: inline-block;padding-left: 5px;"><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p></div><i id="{}" onclick="onOff(event)" class="fa fa-toggle-on" style="margin-right:10px;display:block;float:right;cursor:pointer;color: #03a87c;font-size: 35px;margin-bottom: 5px;vertical-align: top;margin-top: 7px;"></i></div>""".format(img_link,name,i)
        
        tmplist = " ".join(f_id)
        return render_template('choose_send.html',tmplist=tmplist,send_users=finallist,user=user,integrate=integrate, slack_users=slack_final,slacklist=slacklist)
    
    except:
        return render_template('choose_send.html',lex='1',user=user,integrate=integrate,slack_users=slack_final, slacklist=slacklist)

    
    
    
    
    
    
    
    
    
   
    
    
    
    
    
    
######################################################## UPDATE SENT ########################################################
@app.route('/sent/<user>',methods=['GET', 'POST'])
def success(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    sent = db.child(user).child('sent').get().val()
    img_src = "https://firebasestorage.googleapis.com/v0/b/getlex-5b86d.appspot.com/o/congrats%2Fcongrats1.jpg?alt=media&token=98ab4d97-f395-4196-bb42-4be474d43220"
    
    return render_template('success.html',sent=sent,user=user,img_src=img_src)


##################################################### ALL SENT UPDATES #######################################################
@app.route('/archive/<user>',methods=['GET', 'POST'])
def archive(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()

    try:
        updates = [i for i in db.child(user).child('updates').child('days').get().val()]
        all_together = ""
        for i in updates:
            text_ = db.child(user).child('updates').child('days').child(i).child('text').get().val()
            upv = db.child(user).child('updates').child('days').child(i).child('upvotes').child('num').get().val()
            downv = db.child(user).child('updates').child('days').child(i).child('downvotes').child('num').get().val()
            votes = int(upv)-int(downv)
            week_day = get_date_title(i)

            all_together = """<div style="line-height:20px;"><div style="vertical-align:top;display:inline-block;width:50px;"><i onclick="turnGreen(event)" style="font-size:30px;margin:0;text-align:center;width:30px" onclick="formSubmit()" class="fa fa-sort-up"></i><p style="text-align:center;margin:0;padding:0;width:30px">{}</p><i onclick="turnRed(event)" class="fa fa-sort-down" style="font-size:30px;margin:0;text-align:center;width:30px"></i></div><div style="width:90%;padding-bottom:80px;display:inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">{}</p><div style="display: inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 30px;margin-bottom: 1%;width: auto;margin-left:-2px">{}</p></div><p style="font-family:Lato, sans-serif;word-wrap: break-word;margin-left:0.2%;width:100%;border:0px solid transparent !important; box-shadow:none;caret-color: rgb(55, 53, 47);margin-top:10px" >{}</p><div style="display:none;color:black;font-family:Lato, sans-serif;" id="preview"></div</div></div></div>""".format(votes, i, week_day, text_) + all_together
                
        return render_template('archive.html',user=user,templist=all_together,count=count_,img_link=img_url, follow_count=follow_count,following_count=following_count,full_name=full_name)
    
    except:
        return render_template('archive.html',user=user,count=count_,msg='true',img_link=img_url, follow_count=follow_count, following_count=following_count,full_name=full_name)
    
    
##################################################### FOLLOWERS LIST #########################################################
@app.route('/followers/<user>',methods=['GET', 'POST'])
def followers(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
        
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    
    if request.method == 'POST':
        removed = request.form.get('removed',None)
        db.child(user).child('followers').child(removed).remove()
        db.child(removed).child('following').child(user).remove()
        num = int(db.child(user).child('follower-count').get().val())
        db.child(user).update({'follower-count':num-1})
        num_removed = int(db.child(removed).child('following-count').get().val())
        db.child(removed).update({'following-count':num_removed-1})
        return redirect(url_for('followers',user=user))
    
    try:
        followers = [i for i in db.child(user).child('followers').get().val()]
        all_together = ""
        for i in followers:
            first = db.child(i).child('first').get().val()
            last = db.child(i).child('last').get().val()
            name = first + " " + last
            img_tmp = db.child(i).child('p_pic').get().val()

            all_together = """<div style="cursor: pointer;margin-top: 25px;margin-bottom: 25px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 50px;height: 50px;line-height: 30px;cursor: pointer;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;margin-top: 3px;"><strong>{}</strong></p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Reply rate:</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Upvote rate:</p></div><div style="display: inline-block;padding-left: 5px;"><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p></div><div style="vertical-align:middle;display:inline-block;height:50px;margin-left:20px"><p id="{}" onmouseover="darkRed(event)" onmouseleave="lightRed(event)" onclick="formSubmit(event)" style="border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color: #a82103;color: white;border: 1px solid #a82103;border-radius: 4px 4px 4px 4px;font-size: 13px;cursor: pointer;position: relative;flex: 0 0 auto;margin: 0 auto;">Remove</p></div></div>""".format(img_tmp, name, i) + all_together
                
        return render_template('followers.html',user=user,templist=all_together,count=count_,img_link=img_url, follow_count=follow_count,following_count=following_count,full_name=full_name)
    
    except:
        return render_template('followers.html',user=user,count=count_,msg='true',img_link=img_url, follow_count=follow_count, following_count=following_count,full_name=full_name)
    

##################################################### FOLLOWING LIST #########################################################
@app.route('/following/<user>',methods=['GET', 'POST'])
def following(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
        
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    
    if request.method == 'POST':
        removed = request.form.get('removed',None)
        db.child(user).child('following').child(removed).remove()
        db.child(removed).child('followers').child(user).remove()
        num = int(db.child(user).child('following-count').get().val())
        db.child(user).update({'following-count':num-1})
        num_removed = int(db.child(removed).child('follower-count').get().val())
        db.child(removed).update({'follower-count':num_removed-1})
        return redirect(url_for('following',user=user))
        
    
    try:
        followers = [i for i in db.child(user).child('following').get().val()]
        all_together = ""
        for i in followers:
            first = db.child(i).child('first').get().val()
            last = db.child(i).child('last').get().val()
            name = first + " " + last
            img_tmp = db.child(i).child('p_pic').get().val()

            all_together = """<div style="cursor: pointer;margin-top: 25px;margin-bottom: 25px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 50px;height: 50px;line-height: 30px;cursor: pointer;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;margin-top: 3px;"><strong>{}</strong></p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Reply rate:</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">Upvote rate:</p></div><div style="display: inline-block;padding-left: 5px;"><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin-bottom: 0px;">N/A</p></div><div style="vertical-align:middle;display:inline-block;height:50px;margin-left:20px"><p id="{}" onmouseover="darkRed(event)" onmouseleave="lightRed(event)" onclick="formSubmit(event)" style="border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color: #a82103;color: white;border: 1px solid #a82103;border-radius: 4px 4px 4px 4px;font-size: 13px;cursor: pointer;position: relative;flex: 0 0 auto;margin: 0 auto;">Unfollow</p></div></div>""".format(img_tmp, name, i) + all_together
                
        return render_template('following.html',user=user,templist=all_together,count=count_,img_link=img_url, follow_count=follow_count,following_count=following_count,full_name=full_name)
    
    except:
        return render_template('following.html',user=user,count=count_,msg='true',img_link=img_url, follow_count=follow_count, following_count=following_count,full_name=full_name)

    
###################################################### INVITE FRIEND #########################################################
@app.route('/invite/<user>',methods=['GET', 'POST'])
def invite(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))

    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    
    return render_template('invite_friends.html',user=user,img_link=img_url,count=count_, follow_count=follow_count, following_count=following_count,full_name=full_name)
    

######################################################## SEND UPDATE #########################################################
@app.route('/write/<user>',methods=['GET', 'POST'])
def write(user):    
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    tmp = db.child(user).child('updates').child('templates').get().val()
    DATE = cur_date()
    DATE_SLASH = dash_to_slash(DATE)
    DAY = get_date_title(DATE)
        
    if request.method == 'POST':
        text = request.form.get('text',None)
        savetemp = request.form.get('savetemp',None)
        cleartemp = request.form.get('cleartemp',None)
        
        if cleartemp == 'clear':
            db.child(user).child('updates').child('templates').remove()
        
        elif savetemp != '':
            if tmp != None:
                db.child(user).child('updates').child('templates').update({f'temp-{len(tmp)}':savetemp})
                return redirect(url_for('write',user=user))
            else:
                db.child(user).child('updates').child('templates').update({'temp-0':savetemp})
                return redirect(url_for('write',user=user))
        else:
            db.child(user).update({'tmp-text':text})
            return redirect(url_for('choose_send',user=user))
    
    tmp = db.child(user).child('updates').child('templates').get().val()
    if tmp != None:
        end = ''
        out = [i for i in tmp]
        for i in range(len(out)):
            pid_ = f'pid_{i}'
            inid_ = f'inid_{i}'
            name_ = out[i]
            text_ = db.child(user).child('updates').child('templates').child(out[i]).get().val()
            text_ = "&%@%".join(text_.split("'"))
            end += """<p onclick="changeTemplate(event)" id="{}" style="text-align: right;display: flex;margin-bottom: 10%;font-family: Lato, sans-serif;color: #535a60;font-weight: 500;font-size: 11px;padding-top: 3px;padding-bottom: 3px;cursor: pointer;">{}</p><input style="display:none" id="{}" value='{}'>""".format(pid_,name_,inid_,text_)
            
        return render_template('write.html',user=user,templist_=end,date=DATE_SLASH,week_day=DAY,img_link=img_url,count=count_, follow_count=follow_count, following_count=following_count,full_name=full_name)
    
    return render_template('write.html',user=user,date=DATE_SLASH,week_day=DAY,img_link=img_url,count=count_, follow_count=follow_count, following_count=following_count,full_name=full_name)


#############################################################################################################################
@app.route('/read/<user>',methods=['GET', 'POST'])
def read(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    
    if request.method == 'POST':
        repID = request.form.get('repID',None)
        repDATE = request.form.get('repDATE',None)    
        updownVote = request.form.get('updownVote',None)
        
        if updownVote != None and updownVote != '':
            tmp_split = updownVote.split("~~~")
            uid,dateid,vote = tmp_split[0],tmp_split[1],tmp_split[2]
            
            cc = 1
            dd = 1
            if vote == "plus":
                u = db.child(uid).child('updates').child('days').child(dateid).child('upvotes').child('users').get().val()
                for i in u.split("~~~"):
                    if i == user:
                        cc = 0
                        break
                if cc == 1:
                    n = int(db.child(uid).child('updates').child('days').child(dateid).child('upvotes').child('num').get().val())
                    db.child(uid).child('updates').child('days').child(dateid).child('upvotes').update({'num':n+1})
                    db.child(uid).child('updates').child('days').child(dateid).child('upvotes').update({'users':u+"~~~"+user})
                
            elif vote == "min":
                u = db.child(uid).child('updates').child('days').child(dateid).child('downvotes').child('users').get().val()
                for i in u.split("~~~"):
                    if i == user:
                        dd = 0
                        break
                if dd == 1:
                    n = int(db.child(uid).child('updates').child('days').child(dateid).child('downvotes').child('num').get().val())
                    db.child(uid).child('updates').child('days').child(dateid).child('downvotes').update({'num':n+1})
                    db.child(uid).child('updates').child('days').child(dateid).child('downvotes').update({'users':u+"~~~"+user})
                        
            return redirect(url_for('read',user=user))
        
        if repID != '' and repID != None and repDATE != '' and repDATE != None:
            return redirect(url_for('reply',user=user,friend_name=repID,update_date=repDATE,inbox_type='1'))
        
        savetemp = request.form.get('savetemp',None)
        num_tmp = db.child(user).child('updates').child('templates').get().val()
        count = 0
        try:
            for i in num_tmp:
                count += 1
        except:
            pass
        db.child(user).child('updates').child('templates').update({f'temp{count}':savetemp})
        return redirect(url_for('read',user=user))

    try:
        following = [i for i in db.child(user).child('following').get().val()]
        friend_end = ""
        update_end = ""

        for i in range(len(following)):
            first = db.child(following[i]).child('first').get().val()
            updates = db.child(user).child('received').child(following[i]).get().val()
            img_link = db.child(following[i]).child('p_pic').get().val()

            if following[i] == 'JJ5TaGwnn5cbRzfTdP04S5gPj8y1':
                msg = """<p><b>Hi :)</b></p><div><br></div><div>Welcome to <i>Lex</i> - a productivity platform for daily updates.</div><div><br></div><div>Click <a style="color:rgb(3, 168, 124)" href="../write/{}"><b>here</b></a> to send your first update!</div><p></p><div>Click <a style="color:rgb(3, 168, 124)" href="../search/{}"><b>here</b></a> to add your first friend!</div><p></p><div>Click <a style="color:rgb(3, 168, 124)" href="../notifications/{}"><b>here</b></a> to see if anyone added you!</div><p></p>""".format(user,user,user)
                img_link = "https://firebasestorage.googleapis.com/v0/b/getlex-5b86d.appspot.com/o/profile%2FJJ5TaGwnn5cbRzfTdP04S5gPj8y1?alt=media&token=/tmp/Selection_378.png"
                id1 = secrets.token_urlsafe(16)
                id2 = secrets.token_urlsafe(16)
                update_end = """<div class=""><div style="display:inline-block;vertical-align:top;"><img src="{}" style="object-fit: cover;margin-right: 25px;width: 50px;height: 50px;line-height: 30px;cursor: pointer;border-radius: 4px;margin-top:10px;"></div><div style="vertical-align:top;display:inline-block;width:40px;"><i id="{}" onclick="turnGreen(event)" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px" onclick="formSubmit()" class="fa fa-sort-up"></i><p style="text-align:center;margin:0;padding:0;width:30px">{}</p><i id="{}" onclick="turnRed(event)" class="fa fa-sort-down" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px"></i></div><div style="padding-bottom:80px;display:inline-block;width:80%"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">{}</p><div style="display: inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 30px;margin-bottom: 1%;width: auto;margin-left:-2px">{}</p></div><div style="vertical-align:middle;display: inline-block;width: 36px;height:25px;margin-left:15px"></div><div id="popup-name"style="width: 11%;padding: 10px;border: 1px solid #ababaa;position: absolute;background-color: white;margin-left: 10%;min-width: 100px;margin-top: 1%;display: none;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">Name</p><input type="text" style="height: 10px;width: 100%;margin-top: -3px;outline: none;border-top: none;border-left: none;border-right: none;box-shadow: none;font-family: Lato, sans-serif;font-size: 10px;"><div></div></div><p style="font-family:Lato, sans-serif;word-wrap: break-word;margin-left:0.7%;width:100%;border:0px solid transparent !important; box-shadow:none;caret-color: rgb(55, 53, 47);margin-top:-5px" >{}</p><div style="display:none;color:black;font-family:Lato, sans-serif;" id="preview"></div></div></div>""".format(img_link, id1, 0, id2, dash_to_slash(cur_date()), get_date_title(cur_date()),msg) 

                friend_end = """<div style="display: flex;width: 120px;"><img src="{}" style="object-fit: cover;margin-right: 1%;width: 25px;height: 25px;line-height: 30px;cursor: pointer;border-radius: 4px;"><p onclick="showFirst(event)" style="text-align: left;color: #535a60;font-family: Lato, sans-serif;font-weight: 500;cursor: pointer;border: 1px solid transparent;font-size: 15px;padding-left: 5px;vertical-align: middle;text-align: left;line-height: 24px;">{}</p><p style="text-align: center !important;color: #ffffff;font-family: Lato, sans-serif;font-weight: 900;cursor: pointer;border: 1px solid transparent;font-size: 11px;text-align: center;line-height: 14px;border-radius: 10px 10px 10px 10px;height: 16px;width: 21px;background-color:;margin: 0 auto;margin-right: -5px;margin-top: 5px;"></p></div>""".format(img_link,"Lex")
                continue

            try:
                updates = [w for w in updates]
                days = []
                update_lis = []
                upvotes = []
                week_days = []
                try:
                    for o in range(5):
                        j = o-5
                        o = updates[o]
                        days += [get_date_num(o)]
                        week_days += [get_date_title(o)]
                        up=db.child(following[i]).child('updates').child('days').child(o).child('upvotes').child('num').get().val()
                        down=db.child(following[i]).child('updates').child('days').child(o).child('downvotes').child('num').get().val()
                        upvotes += [int(up)-int(down)]
                        update_lis += [db.child(user).child('received').child(following[i]).child(o).get().val()]
                except:
                    pass

                day_ = get_date_num(db.child(user).child('following').child(following[i]).get().val())
                cc = 0
                for jr in days:
                    if jr > day_:
                        cc += 1

                if cc == 0:
                    color = "#FFFFFF"
                else:
                    color = "#FC5783"

                x = 5
                for c in range(len(updates)):
                    date_tmp = dash_to_slash(updates[c])
                    week_day = week_days[c]
                    idpar = following[i] + "~~~" + updates[c]
                    id1 = secrets.token_urlsafe(16)
                    id2 = secrets.token_urlsafe(16)
                    upv = upvotes[c]
                    if following[i] == 'JJ5TaGwnn5cbRzfTdP04S5gPj8y1':
                        text_ = update_lis[c].format(user)
                    else:
                        text_ = update_lis[c]

                    update_end = """<div class="{}"><div style="display:inline-block;vertical-align:top;"><img src="{}" style="object-fit: cover;margin-right: 25px;width: 50px;height: 50px;line-height: 30px;cursor: pointer;border-radius: 4px;margin-top:10px;"></div><div id={} style="vertical-align:top;display:inline-block;width:40px;"><i id="{}" onclick="turnGreen(event)" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px" onclick="formSubmit()" class="fa fa-sort-up"></i><p style="text-align:center;margin:0;padding:0;width:30px">{}</p><i id="{}" onclick="turnRed(event)" class="fa fa-sort-down" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px"></i></div><div style="padding-bottom:80px;display:inline-block;width:80%"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">{}</p><div style="display: inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 30px;margin-bottom: 1%;width: auto;margin-left:-2px">{}</p></div><div style="vertical-align:middle;display: inline-block;width: 36px;height:25px;margin-left:15px"><div class="hover-green" onclick="reroutReply(event)" id="{}" style="margin-bottom:30px;border: 1px solid black;padding-left: 3px;padding-right: 3px;padding-top: 2px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color: #03a87c;color: white;border: 1px solid #03a87c;border-radius: 4px 4px 4px 4px;font-size: 11px;cursor: pointer;position: relative;flex: 0 0 auto;margin: 0 auto;">Reply<p style="display:none">{}</p><p style="display:none">{}</p></div></div><div id="popup-name"style="width: 11%;padding: 10px;border: 1px solid #ababaa;position: absolute;background-color: white;margin-left: 10%;min-width: 100px;margin-top: 1%;display: none;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">Name</p><input type="text" style="height: 10px;width: 100%;margin-top: -3px;outline: none;border-top: none;border-left: none;border-right: none;box-shadow: none;font-family: Lato, sans-serif;font-size: 10px;"><div></div></div><p style="font-family:Lato, sans-serif;word-wrap: break-word;margin-left:0.7%;width:100%;border:0px solid transparent !important; box-shadow:none;caret-color: rgb(55, 53, 47);margin-top:-5px" >{}</p><div style="display:none;color:black;font-family:Lato, sans-serif;" id="preview"></div></div></div>""".format(f'large-{first}', img_link, idpar, id1, upv, id2, date_tmp, week_day, secrets.token_urlsafe(16), following[i], updates[c], text_) + update_end  

            except:
                color = "#FFFFFF"
                cc = 0

            friend_end += """<div style="display: flex;width: 120px;"><img src="{}" style="object-fit: cover;margin-right: 1%;width: 25px;height: 25px;line-height: 30px;cursor: pointer;border-radius: 4px;"><p onclick="showFirst(event)" id="{}" style="text-align: left;color: #535a60;font-family: Lato, sans-serif;font-weight: 500;cursor: pointer;border: 1px solid transparent;font-size: 15px;padding-left: 5px;vertical-align: middle;text-align: left;line-height: 24px;">{}</p><p style="text-align: center !important;color: #ffffff;font-family: Lato, sans-serif;font-weight: 900;cursor: pointer;border: 1px solid transparent;font-size: 11px;text-align: center;line-height: 14px;border-radius: 10px 10px 10px 10px;height: 16px;width: 21px;background-color: {};margin: 0 auto;margin-right: -5px;margin-top: 5px;">{}</p></div>""".format(img_link,first,first,color,cc)

        count_ = db.child(user).child('sent').get().val()
        follow_count = db.child(user).child('follower-count').get().val()
        following_count = db.child(user).child('following-count').get().val()
        return render_template('read.html',user=user,friendslist=friend_end,updateslist=update_end,img_link=img_url, count=count_, follow_count=follow_count, following_count=following_count,full_name=full_name)
    
    except:
        return render_template('no_friends.html',user=user,img_link=img_url,count=count_, follow_count=follow_count, following_count=following_count,full_name=full_name)

    
#############################################################################################################################
@app.route('/search/<user>',methods=['GET', 'POST'])
def search(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
        
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    img_link = db.child(user).child('p_pic').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    
    if request.method == 'POST':
        userid = request.form.get('userid',None)
        search = request.form.get('search',None)

        if userid != None:
            db.child(userid).child('requests').update({user:cur_date()})
            db.child(user).child('requested').update({userid:cur_date()})

        if search != None:
            search = search.lower()
            
            final = []
            names = []
            for i in db.get().val():
                if i != user:
                    first = db.child(i).child('first').get().val().lower()
                    last = db.child(i).child('last').get().val().lower()
                    name = first+" "+last
                    if search in name:
                        final += [i]
                        names += [name]
            
            try:
                following = [i for i in db.child(user).child('following').get().val()]
                following = "".join(following)
            except:
                following = ""
            try:
                requested = [i for i in db.child(user).child('requested').get().val()]
                requested = "".join(requested)
            except:
                requested = ""
                        
            end = ""
            if len(final) > 0:
                for i in range(len(final)):
                    fullid_ = f'fullid_{i}'
                    halfid_ = f'halfid_{i}'
                    quarterid_ = f'quarterid_{i}'
                    userid_ = f'userid_{i}'
                    img_link1 = db.child(final[i]).child('p_pic').get().val()
                    
                    follow = "Follow"
                    color = "#03a87c"
                    onclick = 'onclick="followUser(event)" id="yeet-9"'
                    text_col = "white"
                    cursor = "pointer"
                    if final[i] in following:
                        follow = "Following"
                        color = "white"
                        text_col = "black"
                        onclick = ''
                        cursor = "not-allowed"
                    elif final[i] in requested:
                        follow = "Requested"
                        color = "white"
                        text_col = "black"
                        onclick = ''
                        cursor = "not-allowed"
                        
                    end += """<form method="post" id="{}"><div id="{}" style="padding-top: 10px;padding-bottom: 10px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 40px;height: 40px;line-height: 30px;border-radius: 5px;"></div><div id="{}" style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p {} style="height: 20px;border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color:{};color: {};border: 1px solid #03a87c;border-radius: 5px 5px 5px 5px;font-size: 11px;cursor: {};display: inline-block;margin-top: 4px;">{}</p><input value="{}" name="userid" style="display:none"></p></div></div></form>""".format(fullid_,halfid_,img_link1,quarterid_,names[i],onclick,color,text_col,cursor,follow,final[i])                    
            
            if end == "":
                return render_template('search.html',user=user,img_link=img_link,msg="0 results found.",count=count_,follow_count=follow_count, following_count=following_count)
            return render_template('search.html',user=user,search_users=end,img_link=img_link,count=count_,follow_count=follow_count, following_count=following_count,full_name=full_name)
    
    return render_template('search.html',user=user,img_link=img_link,count=count_,follow_count=follow_count, following_count=following_count,full_name=full_name)
    
    
#############################################################################################################################
@app.route('/reply/<user>/<friend_name>/<update_date>/<inbox_type>',methods=['GET', 'POST'])
def reply(user,friend_name,update_date,inbox_type):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()
    ids_ = []
    texts_ = []
    date = cur_date()
    day = get_date_title(update_date)
    img_link1 = db.child(user).child('p_pic').get().val()
    date = cur_date()
    replies = ""
    cc = 0
    
    if inbox_type == '0':
        update = db.child(user).child('updates').child('days').child(update_date).child('text').get().val()
        path_= db.child(user).child('updates').child('days').child(update_date).child('replies').child(friend_name).get().val()
        if path_ != None and path_ != '':
            for i in path_:
                ids_ += [i['id']]
                texts_ += [i['text']]
                cc += 1
        path_2=db.child(user).child('inbox-replies').child(user).child(update_date).get().val()
        dd = 0
        if path_2 != None:
            for i in path_2:
                dd += 1
                
    elif inbox_type == '1':
        update = db.child(friend_name).child('updates').child('days').child(update_date).child('text').get().val()
        path_= db.child(friend_name).child('updates').child('days').child(update_date).child('replies').child(user).get().val()
        if path_ != None:
            for i in path_:
                ids_ += [i['id']]
                texts_ += [i['text']]
                cc += 1
        path_2 = db.child(friend_name).child('inbox-replies').child(user).child(update_date).get().val()
        dd = 0
        if path_2 != None:
            for i in path_2:
                dd += 1
    
    if request.method == 'POST':
        reply = request.form.get('reply',None)
        if inbox_type == '0':
            db.child(friend_name).child('inbox').child(user).child(update_date).update({dd:{'id':user,'text':reply,'date':date}})
            db.child(user).child('updates').child('days').child(update_date).child('replies').child(friend_name).update({cc:{'text':reply,'date':date,'id':user}})
        elif inbox_type == '1':
            db.child(friend_name).child('inbox-replies').child(user).child(update_date).update({dd:{'id':user,'text':reply,'date':date}})
            db.child(friend_name).child('updates').child('days').child(update_date).child('replies').child(user).update({cc:{'text':reply,'date':date,'id':user}})
        return redirect(url_for('reply',user=user,friend_name=friend_name,update_date=update_date,inbox_type=inbox_type))
                
                
    if cc > 0:
        for i in range(len(ids_)):
            img_link = db.child(ids_[i]).child('p_pic').get().val()
            name = db.child(ids_[i]).child('first').get().val() + " " + db.child(ids_[i]).child('last').get().val()
            replies += """<div><div style="float: left;"><img src="{}" style="object-fit: cover;width: 30px;height: 30px;line-height: 30px;cursor: pointer;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 3px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p style="max-width: 250px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;">{}</p></div></div>""".format(img_link,name,texts_[i])

    return render_template('reply.html',user=user,replies=replies,update=update,img_link=img_link1,date=update_date,day=day, count=count_,follow_count=follow_count, following_count=following_count, full_name=full_name)


#############################################################################################################################
# @app.route('/profile/<user>',methods=['GET', 'POST'])
# def profile(user):
#     try:
#         if session['id'] != user:
#             return redirect(url_for('not_logged_in'))
#     except:
#         return redirect(url_for('not_logged_in'))
    
#     count_ = db.child(user).child('sent').get().val()
#     follow_count = db.child(user).child('follower-count').get().val()
#     following_count = db.child(user).child('following-count').get().val()
#     followers = db.child(user).child('profile').child('followers').get().val()
#     sent = db.child(user).child('profile').child('sent').get().val()
    
#     cc = 0
#     try:
#         out = [i for i in db.child(user).child('updates').child('days').get().val()]
#         end = ""
#         x = 5
        
#         for i in range(x):
#             try:
#                 c = -(x-i)
#                 date = get_date_cur(out[c])
#                 title = get_date_title(out[c])  
#                 dv=int(db.child(user).child('updates').child('days').child(out[c]).child('downvotes').child('num').get().val())
#                 uv=int(db.child(user).child('updates').child('days').child(out[c]).child('upvotes').child('num').get().val())
#                 votes = uv-dv
#                 text = db.child(user).child('updates').child('days').child(out[c]).child('text').get().val()
                
#                 end = """<div style="margin-bottom:40px"><div style="display:inline-block;width:50px;"><i style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px" class="fa fa-sort-up"></i><p style="text-align:center;margin:0;padding:0;width:30px">{}</p><i class="fa fa-sort-down" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px"></i></div><div style="display:inline-block"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">{}<p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 30px;margin-bottom: 1%;width: auto;">{}</p><div style="line-height:18px;font-size:14px;font-family:Lato, sans-serif; outline:0px solid transparent;margin-left:0.2%;width:100%;height:100%;border:0px solid transparent !important; box-shadow:none;caret-color: rgb(55, 53, 47);margin-top:10px !important">{}</div></div></div></div>""".format(votes,date,title,text) + end
                
#             except:
#                 pass
#         cc = 1
#     except:
#         pass
    
#     first = db.child(user).child('first').get().val()
#     last = db.child(user).child('last').get().val()
#     img_link = db.child(user).child('p_pic').get().val()
#     name = f'{first} {last}'
    
#     if cc == 0:
#         return render_template('profile.html',followers=followers,sent=sent,user=user,name=name,img_link=img_link,count=count_,follow_count=follow_count, following_count=following_count)
#     else:
#         return render_template('profile.html',followers=followers,sent=sent,user=user,name=name,img_link=img_link,date=date, last_update=end,count=count_,follow_count=follow_count, following_count=following_count)


#############################################################################################################################


@app.route('/notifications/<user>',methods=['GET', 'POST'])
def notifications(user):
    try:
        if session['id'] != user:
            return redirect(url_for('not_logged_in'))
    except:
        return redirect(url_for('not_logged_in'))
    
    img_url = db.child(user).child('p_pic').get().val()
    full_name = db.child(user).child('first').get().val() + " " + db.child(user).child('last').get().val()
    count_ = db.child(user).child('sent').get().val()
    follow_count = db.child(user).child('follower-count').get().val()
    following_count = db.child(user).child('following-count').get().val()

    if request.method == 'POST':
        accept_or_ignore = request.form.get('accept_ignore',None).split(" ")
        choice = accept_or_ignore[1]
        user_id = accept_or_ignore[0]
        
        if choice == "accept":
            db.child(user).child('requests').child(user_id).remove()
            db.child(user).child('followers').update({user_id:cur_date()})
            db.child(user_id).child('requested').child(user).remove()
            db.child(user_id).child('following').update({user:cur_date()})
            num = db.child(user).child('follower-count').get().val()
            db.child(user).update({'follower-count':int(num)+1})
            num_other = db.child(user_id).child('following-count').get().val()
            db.child(user_id).update({'following-count':int(num_other)+1})
        elif choice == "ignore":
            db.child(user).child('requests').child(user_id).remove()
            db.child(user_id).child('requested').child(user).remove()
    
    mydict = {}
    fr = db.child(user).child('inbox').get().val()
    if fr != None:
        fr = [i for i in fr]
        for i in fr:
            for o in db.child(user).child('inbox').child(i).get().val():
                notifs = ""
                days1 = get_date_num(o)
                days2 = get_date_num(db.child(user).child('last-log').get().val())
                color = " "
                if days1 > days2:
                    color = '#FC5783'

                date_tmp = "/".join(o.split('-'))
                notifs += """#@%$<div><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin: 0px;margin-top: 20px;">{}</p><hr style="margin-top:0px;background-color:{}"></div>""".format(date_tmp,color)
                
                count = 0
                for w in db.child(user).child('inbox').child(i).child(o).get().val():                
                    first = db.child(i).child('first').get().val()
                    last = db.child(i).child('last').get().val()
                    name = first+" "+last
                    text = db.child(user).child('inbox').child(i).child(o).child(count).child('text').get().val()
                    count += 1
                    
                    if len(w) > 100:
                        text = w[0:100] + "..."
                        
                    img_link = db.child(i).child('p_pic').get().val()
                    notifs += """<a style="color:black" href="../reply/{}/{}/{}/{}"><div style="cursor: pointer;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 30px;height: 30px;line-height: 30px;cursor: pointer;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 3px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;">{}</p></div></div></a>""".format(user,i,o,'1',img_link,name,text)
                
                mydict[o] = notifs
        
    fr = db.child(user).child('inbox-replies').get().val()
    if fr != None:
        fr = [i for i in fr]
        for i in fr:
            for o in db.child(user).child('inbox-replies').child(i).get().val():
                notifs = ""
                days1 = get_date_num(o)
                days2 = get_date_num(db.child(user).child('last-log').get().val())
                color = " "
                if days1 > days2:
                    color = '#FC5783'

                date_tmp = "/".join(o.split('-'))
                jjj = """#@%$<div><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;margin: 0px;margin-top: 20px;">{}</p><hr style="margin-top:0px;background-color:{}"></div>""".format(date_tmp,color)
                
                count = 0
                for w in db.child(user).child('inbox-replies').child(i).child(o).get().val():                
                    first = db.child(i).child('first').get().val()
                    last = db.child(i).child('last').get().val()
                    name = first+" "+last
                    text = db.child(user).child('inbox-replies').child(i).child(o).child(count).child('text').get().val()
                    count += 1
                    
                    if len(w) > 100:
                        text = w[0:100] + "..."
                        
                    img_link = db.child(i).child('p_pic').get().val()
                    notifs += """<a style="color:black" href="../reply/{}/{}/{}/{}"><div style="cursor: pointer;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 30px;height: 30px;line-height: 30px;cursor: pointer;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 3px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p style="max-width: 600px;font-weight: 400;line-height: 16px;font-family: Lato, sans-serif;">{}</p></div></div></a>""".format(user,i,o,'0',img_link,name,text)
                                
                try:
                    mydict[o] = mydict[o] + notifs
                except:
                    mydict[o] = jjj+notifs
            
    notifs = ""
    for i in mydict:
        notifs += mydict[i]
        
    notifs = notifs.split('#@%$')
#     notifs.reverse()
    notifs = "".join(notifs)
    db.child(user).update({'last-log':cur_date()})
    
    try:
        req = [i for i in db.child(user).child('requests').get().val()]
        requests = ""
        for i in req:
            first = db.child(i).child('first').get().val()
            last = db.child(i).child('last').get().val()
            name = first + " " + last
            img_link_ = db.child(i).child('p_pic').get().val()
            date = dash_to_slash(db.child(user).child('requests').child(i).get().val())
            
            requests += """<p style="font-family: Lato, sans-serif;margin-bottom:-4px;margin-top:30px" >{}</p><hr style="margin-bottom:10px"></hr><div style="padding-top: 10px;padding-bottom: 10px;"><div style="float: left;"><img src="{}" style="object-fit: cover;width: 40px;height: 40px;line-height: 30px;border-radius: 5px;"></div><div style="display: inline-block;padding-left: 10px;"><p style="margin-bottom: 2px;font-family: Lato, sans-serif;"><strong>{}</strong></p><p id="{}" onclick="formSubmit(event)" style="height: 20px;border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color:#03a87c;color: white;border: 1px solid #03a87c;border-radius: 5px 5px 5px 5px;font-size: 11px;cursor: pointer;display: inline-block;margin-top: 4px;">Accept</p><div style="display:inline-block;width:10px"></div><p id="{}" onclick="formSubmit(event)" style="height: 20px;border: 1px solid black;padding-left: 5px;padding-right: 5px;padding-top: 4px;padding-bottom: 2px;font-family: Lato, sans-serif;background-color:#a82103;color: white;border: 1px solid #a82103;border-radius: 5px 5px 5px 5px;font-size: 11px;cursor: pointer;display: inline-block;margin-top: 4px;">Ignore</p></div></div>""".format(date,img_link_,name,i+" accept",i+" ignore")
            
    except:
        requests = ""

    msg_notifs = ""
    msg_requests = ""
    if notifs == "":
        msg_notifs = "true"
    if requests == "":
        msg_requests = "true"
        
    return render_template('notifications.html',user=user,notifs=notifs,img_link=img_url,count=count_,follow_count=follow_count, following_count=following_count,msg_requests=msg_requests,msg_notifs=msg_notifs,requests=requests,full_name=full_name)


########################################################################################################################


# @app.route('/afewthings/<user>',methods=['GET', 'POST'])
# def afewthings(user):
#     try:
#         if session['id'] != user:
#             return redirect(url_for('not_logged_in'))
#     except:
#         return redirect(url_for('not_logged_in'))
    
#     if request.method == 'POST':
#         return redirect(url_for('write',user=user))
    
#     return render_template('before_you_start.html',user=user)


########################################################################################################################


if __name__ == '__main__':
    app.run(debug=True)
    
    
    
    
    
    
    
    
    
    
#                 update_end = """<div class="{}"><div id={} style="vertical-align:top;display:inline-block;width:50px;"><i id="{}" onclick="turnGreen(event)" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px" onclick="formSubmit()" class="fa fa-sort-up"></i><p style="text-align:center;margin:0;padding:0;width:30px">{}</p><i id="{}" onclick="turnRed(event)" class="fa fa-sort-down" style="cursor:pointer;font-size:30px;margin:0;text-align:center;width:30px"></i></div><div style="padding-bottom:80px;display:inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">{}</p><div style="display: inline-block;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 30px;margin-bottom: 1%;width: auto;">{}</p></div><div style="display: inline-block;width: 100px;"><i onclick="saveTemplate()" class="la la-arrow-circle-o-down" style="margin-left: 20%;font-size: 16px;cursor: pointer;"></i><i id="{}" onclick="reroutReply(event)" class="la la-comment-o" style="margin-left: 8%;font-size: 16px;cursor: pointer;margin-bottom: 0px;"><p style="display:none">{}</p><p style="display:none">{}</p></i></div><div id="popup-name"style="width: 11%;padding: 10px;border: 1px solid #ababaa;position: absolute;background-color: white;margin-left: 10%;min-width: 100px;margin-top: 1%;display: none;"><p style="text-align: right;display: flex;font-family: Lato, sans-serif;font-size: 11px;margin-bottom: 5px;">Name</p><input type="text" style="height: 10px;width: 100%;margin-top: -3px;outline: none;border-top: none;border-left: none;border-right: none;box-shadow: none;font-family: Lato, sans-serif;font-size: 10px;"><div></div></div><p style="font-family:Lato, sans-serif;word-wrap: break-word;margin-left:0.5%;width:100%;border:0px solid transparent !important; box-shadow:none;caret-color: rgb(55, 53, 47);margin-top:10px" >{}</p><div style="display:none;color:black;font-family:Lato, sans-serif;" id="preview"></div></div></div>""".format(f'large-{first}',idpar, id1, upv, id2, date_tmp, week_day, secrets.token_urlsafe(16), following[i], updates[c], text_) + update_end  
    
    
    
    
    
    
    
    
    
    
    
