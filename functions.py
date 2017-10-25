import os, sys, requests, subprocess, hashlib, mysql.connector, boto3
from urllib.parse import urlparse

from PIL import Image, ImageFilter
from config import mysql_op

cnx = mysql.connector.connect(
    user=mysql_op['user'], 
    password=mysql_op['password'],
    host=mysql_op['host'],
    port=mysql_op['port'],
    database=mysql_op['database'])
cursor = cnx.cursor()

def isGoodObject(object_url, allowed_extensions):
    path_to_test = urlparse(object_url).path
    try:
        extension_to_test = os.path.splitext(path_to_test)[1]
        if extension_to_test in allowed_extensions:
            return True
    except Exception as e:
        print(e)

# attempts to grab an object from a given url, if it succeeds we stash and return info about object
def grabbedObject(object_url, allowed_mimes, storage_profiles, object_new_reference):
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
        print('hash is familiar...')
    except Exception as e:
        print(e)

# manage cropping attempts
def cropImage(object_storage_path, object_final_reference, object_mime, pixel_adjust):
    if pixel_adjust:
        if 'jpeg' in object_mime:
            try:
                img = Image.open(object_storage_path + object_final_reference)
                w, h = img.size
                cropped = img.crop((0, 0, w, h-pixel_adjust))
                cropped.save(object_storage_path + object_final_reference, format='JPEG', subsampling=0, quality=90)
            except Exception as e:
                print(e)

# manage transfer to S3
def uploadToS3(object_storage_path, object_final_reference, object_mime, s3_bucket):
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

# manage creation of still images from mp4 files
def stillImageFromVideo(object_storage_path, object_final_reference, still_object_path, still_object_reference):
    # run ffmpg command to save frame 1 as a jpg.
    # TODO this should be catching errors
    # dynamic frame selection and quality attrs
    # make attributes lists and change shell=True to shell=False
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
    try:
        global cnx
        global cursor
        # inject object data into database
        insert = ("INSERT INTO objects_grabbed SET object_title = %s, object_reference = %s, object_type = %s, site_tag = %s, created_date = NOW()")
        cursor.execute(insert, (object_title, object_final_reference, object_type, site_tag))
        cnx.commit()
    except Exception as e:
        print(e)
    