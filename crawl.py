import sys, time, os, praw, uuid
from config import *
from functions import *

allowed_extensions = storage_profiles['allowed_extensions']
allowed_mimes = storage_profiles['allowed_mimes']
s3_bucket = storage_profiles['s3_bucket']
still_image_storage_path = storage_profiles['video_still']

for site_key, pull_list in site_block.items():
    if 'reddit' in site_key:
        allowed_sources = reddit_profile['allowed_sources']
        sleep_seconds = reddit_profile['sleep_seconds']
        pixel_adjust = reddit_profile['crop']
        # connect to reddit
        reddit = praw.Reddit(client_id=reddit_op['client_id'],
                     client_secret=reddit_op['client_secret'],
                     password=reddit_op['password'],
                     user_agent=reddit_op['user_agent'],
                     username=reddit_op['username'])
        print('Processing Reddit...')
        for pull_source in pull_list:
            print('\t/r/' + pull_source[0])
            for submission in reddit.subreddit(pull_source[0]).hot(limit=25):
                site_tag = pull_source[1]
                # check if submission domain is allowed. this is reddit specific.
                if submission.domain in allowed_sources:
                    object_url = submission.url
                    object_title = submission.title
                    object_source_tag = pull_source[1]
                    object_new_reference = str(uuid.uuid4()) # new name for stashing and saving
                    # check if it's an object i can handle
                    if isGoodObject(object_url, allowed_extensions):
                        # attempt to grab the object. if object is grabbed and unique expect object details
                        grabbed_object = grabbedObject(object_url, allowed_mimes, storage_profiles, object_new_reference)
                        if grabbed_object:
                            object_mime = grabbed_object[0]
                            object_final_reference = grabbed_object[1]
                            object_storage_path = grabbed_object[2]
                            storage_type = grabbed_object[3]
                            # finish object handling based on type
                            if storage_type == 0:
                                # image type, attempt crop, stash in s3
                                cropImage(object_storage_path, object_final_reference, object_mime, pixel_adjust)
                                
                            elif storage_type == 1:
                                # video type, create still image and send to s3
                                stillImageFromVideo(object_storage_path, object_final_reference, still_image_storage_path, object_final_reference.replace("mp4", "jpeg"))
                                uploadToS3(still_image_storage_path, object_final_reference.replace('mp4', 'jpeg'), 'image/jpeg', s3_bucket)
                            # send object to s3
                            uploadToS3(object_storage_path, object_final_reference, object_mime, s3_bucket)
                            # store details in database
                            storeObjectDetails(object_title, object_final_reference, storage_type, site_tag)
                            try:
                                print('clearing files...')
                                os.remove(object_storage_path + object_final_reference)
                                os.remove(still_image_storage_path + object_final_reference.replace('mp4', 'jpeg'))
                            except OSError as e:
                                print(e)
                            print('did one... sleeping for ' + str(sleep_seconds) + ' seconds...')
        if sleep_seconds:
            time.sleep(sleep_seconds)
    elif 'yourkeyhere':
        # here is probably a good spot for site specific handling rules
        pass