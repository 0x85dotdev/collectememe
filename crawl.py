import hashlib
import os
import subprocess
import sys
import time
import uuid
from urllib.parse import urlparse

import boto3
import mysql.connector
import praw
import requests
from PIL import Image, ImageFilter

from config import *

# from functions import *

# This should be cleaned out
allowed_extensions = storage_profiles['allowed_extensions']
allowed_mimes = storage_profiles['allowed_mimes']
s3_bucket = storage_profiles['s3_bucket']
still_image_storage_path = storage_profiles['video_still']

## Start pre run tests

# Test for ffmpeg if video/mp4 is in mime config
# Maybe we test the ffmpeg python lib performance sometime
if 'video/mp4' in allowed_mimes:
    ffmpeg_path = subprocess.run(['which', 'ffmpeg'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    if not ffmpeg_path:
        print("no ffmpeg installed, can't process video/mp4!")
        sys.exit(0)

# Make sure if uploading to s3 that aws-cli (aws) is installed
if stash_in_s3 is not False:
    aws_cli_path = subprocess.run(['which', 'aws'], stdout=subprocess.PIPE).stdout.decode('utf-8')
    if not aws_cli_path:
        print("no aws-cli installed, can't upload to s3!")
        sys.exit(0)

# Make sure we can connect to the database
try:
    cnx = mysql.connector.connect(
        user=mysql_op['user'], 
        password=mysql_op['password'],
        host=mysql_op['host'],
        port=mysql_op['port'],
        database=mysql_op['database']
    )
    cursor = cnx.cursor()
except Exception:
    print("Couldn't connect a database!")
    sys.exit(0)

## End pre run tests


## Start various functions

def isGoodObject(object_url, allowed_extensions):
    """
    Return True if object has an allowed extension
    """
    path_to_test = urlparse(object_url).path
    try:
        extension_to_test = os.path.splitext(path_to_test)[1]
        if extension_to_test in allowed_extensions:
            return True
        return False
    except Exception as e:
        print(e)

# 
def grabbedObject(object_url, allowed_mimes, storage_profiles, object_new_reference):
    """ 
    Returns in a very convoluted way, currently.
    Attempts to grab an object from a given url, if it succeeds we stash and return info about object
    """
    try:
        # make sure on reguest any gifv are pulled as mp4
        data_request = requests.get(object_url.replace("gifv", "mp4"))
        object_mime = str(data_request.headers['Content-Type'])
        if object_mime in allowed_mimes:
            object_final_reference = object_new_reference + "." + object_mime.split('/')[1]
            # write a file
            storage_type = 0 # default 0 for image
            storage_path = storage_profiles['image']
            if 'video/mp4' in object_mime:
                storage_type = 1
                storage_path = storage_profiles['video']
            with open(storage_path + object_final_reference, 'wb') as handler:
                handler.write(data_request.content) # save binary data as object
                handler.close()
            
            # test if file actually exists. if true, compare hash. if unique return else delete object
            if os.path.isfile(storage_path + object_final_reference):
                object_md5 = hashlib.md5()
                object_md5.update(open(storage_path + object_final_reference, 'rb').read())
                md5_to_test = object_md5.hexdigest()
                if isUniqueHash(md5_to_test):
                    return object_mime, object_final_reference, storage_path, storage_type
                os.remove(storage_path + object_final_reference)
    except Exception as e:
        print(e)

# return true if hash is unique, false if hash exists
def isUniqueHash(hash_to_check, hash_type_to_check='md5'):
    """ 
    Returns True if the md5 has is unique to our storage
    """
    try:
        global cnx
        global cursor
        test_hash_query = ("select * from hash_storage where md5 = %s")
        cursor.execute(test_hash_query, (hash_to_check,))
        row = cursor.fetchone()
        if not row:
            sql = "INSERT INTO hash_storage SET md5 = %s"
            cursor.execute(sql, (hash_to_check,))
            cnx.commit()
            return True
        else:
            return False
    except Exception as e:
        print(e)

def cropImage(object_storage_path, object_final_reference, object_mime, pixel_adjust):
    """
    Crop a given image object according to given parameters
    manage cropping attempts
    """
    if pixel_adjust:
        if 'jpeg' in object_mime:
            try:
                img = Image.open(object_storage_path + object_final_reference)
                w, h = img.size
                cropped = img.crop((0, 0, w, h-pixel_adjust))
                cropped.save(object_storage_path + object_final_reference, format='JPEG', subsampling=0, quality=90)
            except Exception as e:
                print(e)

def uploadToS3(object_storage_path, object_final_reference, object_mime, s3_bucket):
    """
    Manage transfer of object to S3 
    """
    if not s3_bucket:
        print("skipping s3 upload, add bucket in config if desired...")
    else:
        # upload to s3 :X
        try:
            s3 = boto3.resource('s3')
            data = open(object_storage_path + object_final_reference, 'rb')
            s3.Bucket(s3_bucket).put_object(Key=object_storage_path + object_final_reference, Body=data, ContentType=object_mime)
        except Exception as e:
            print(e)

def stillImageFromVideo(object_storage_path, object_final_reference, still_object_path, still_object_reference):
    """
    manage creation of still images from mp4 files
    Run ffmpg command to save frame 1 as a jpg.
    TODO this should be catching errors
    dynamic frame selection and quality attrs
    make attributes lists and change shell=True to shell=False
    """
    try:
        subprocess.run("ffmpeg -hide_banner -loglevel panic -ss 2 -i {} -qscale:v 31 -vframes 1 {}".format(object_storage_path + object_final_reference, still_object_path + still_object_reference), shell=True)

        # only run if the still image was created. 
        # bandaid till i error check ffmpeg
        if(os.path.isfile(still_object_path + still_object_reference)):
            # open transparent png overlay file as RGBA so we can safely paste it later
            play_button_image = Image.open('static/play_button_overlay.png').convert('RGBA')
            # open bg image. apply blur and dim
            # TODO make filter and blur attrs dynamic
            background_image = Image.open(still_object_path + still_object_reference).filter(ImageFilter.GaussianBlur(4)).point(lambda i: i * .75)
            # do an initial low quality save. this is a hacky way to make the overal image size smaller
            background_image.save(still_object_path + still_object_reference, quality=70)

            #open it again and get w/h
            background_image = Image.open(still_object_path + still_object_reference)
            bg_w, bg_h = background_image.size

            # paste images together
            # TODO make bg_w/h attrs dynamic based on play_button image size?
            background_image.paste(play_button_image, ((bg_w-128)//2, (bg_h-128)//2), play_button_image)
            # save with highest quality so the play button looks good. This could likely be tweaked more
            background_image.save(still_object_path + still_object_reference, format='JPEG', subsampling=0, quality=100)
            return True
    except Exception as e:
        print(e)

def storeObjectDetails(object_title, object_final_reference, object_type, site_tag):
    """
    inject object data into database
    """
    try:
        global cnx
        global cursor

        insert = ("INSERT INTO objects_grabbed SET object_title = %s, object_reference = %s, object_type = %s, site_tag = %s, created_date = NOW()")
        cursor.execute(insert, (object_title, object_final_reference, object_type, site_tag))
        cnx.commit()
    except Exception as e:
        print(e)

## End various functions

# Iterate each item in crawlable and handle it
# This should be threaded where it's allowed (reddit probably won't like this)
for site, rules in crawlable.items():
    if site == 'reddit':
        count_per_page = rules.get('count_per_page')
        # connect to reddit
        reddit = praw.Reddit(
            client_id = rules.get('authenticate')['client_id'],
            client_secret = rules.get('authenticate')['client_secret'],
            password = rules.get('authenticate')['password'],
            user_agent = rules.get('authenticate')['user_agent'],
            username = rules.get('authenticate')['username'],
        )
        # Get crawlable user or subreddit
        for crawl_type, crawl_pages in rules.get('crawl').items():
            if crawl_type == 'subreddits':
                for subreddit in crawl_pages:
                    for submission in reddit.subreddit(subreddit).hot(limit=count_per_page):
                        print(submission.domain)

    #     sys.exit(0)
    #     for pull_source in pull_list:
    #         print('\t/r/' + pull_source[0])
    #         for submission in reddit.subreddit(pull_source[0]).hot(limit=reddit_profile['item_count']):
    #             site_tag = pull_source[1]
    #             # check if submission domain is allowed. this is reddit specific.
    #             print('trying' + submission.url)
    #             if submission.domain in allowed_sources:
    #                 object_url = submission.url
    #                 object_title = submission.title
    #                 object_source_tag = pull_source[1]
    #                 object_new_reference = str(uuid.uuid4()) # new name for stashing and saving
    #                 # check if it's an object i can handle
    #                 if isGoodObject(object_url, allowed_extensions):
    #                     # attempt to grab the object. if object is grabbed and unique expect object details
    #                     grabbed_object = grabbedObject(object_url, allowed_mimes, storage_profiles, object_new_reference)
    #                     if grabbed_object:
    #                         object_mime = grabbed_object[0]
    #                         object_final_reference = grabbed_object[1]
    #                         object_storage_path = grabbed_object[2]
    #                         storage_type = grabbed_object[3]
    #                         # finish object handling based on type
    #                         if storage_type == 0:
    #                             # image type, attempt crop, stash in s3
    #                             cropImage(object_storage_path, object_final_reference, object_mime, pixel_adjust)
                                
    #                         elif storage_type == 1:
    #                             # video type, create still image and send to s3
    #                             stillImageFromVideo(object_storage_path, object_final_reference, still_image_storage_path, object_final_reference.replace("mp4", "jpeg"))
    #                             uploadToS3(still_image_storage_path, object_final_reference.replace('mp4', 'jpeg'), 'image/jpeg', s3_bucket)
    #                         # send object to s3
    #                         uploadToS3(object_storage_path, object_final_reference, object_mime, s3_bucket)
    #                         # store details in database
    #                         storeObjectDetails(object_title, object_final_reference, storage_type, site_tag)
    #                         if not keep_local_files:
    #                             try:
    #                                 print('clearing files...')
    #                                 os.remove(object_storage_path + object_final_reference)
    #                                 os.remove(still_image_storage_path + object_final_reference.replace('mp4', 'jpeg'))
    #                             except OSError as e:
    #                                 print(e)
    #         if sleep_seconds:
    #             print('sleeping ' + str(sleep_seconds) + 's')
    #             time.sleep(sleep_seconds)
    # elif 'yourkeyhere':
    #     # here is probably a good spot for site specific handling rules
    #     pass
