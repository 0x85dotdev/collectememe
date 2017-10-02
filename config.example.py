##
## manage server credentials
##

mysql_op = {
    'user' : 'homestead',
    'password' : 'secret',
    'host' : '127.0.0.1',
    'port' : '3306',
    'database' : 'collectememe',
}

reddit_op = {
    'client_id' : '',
    'client_secret' : '',
    'password' : '',
    'user_agent' : '',
    'username' : ''
}

storage_profiles = {
    'video' : 'storage/video/',
    'video_still' : 'storage/video_still/',
    'image' : 'storage/image/',
    'allowed_mimes' : ['video/mp4', 'image/jpeg', 'image/png', 'image/gif'],
    'allowed_extensions' : ['.mp4', '.jpeg', '.jpg', '.png', '.gif', '.gifv'],
    's3_bucket' : ''
}

# block of subreddits to process with labels for database storage
site_block = {
    'reddit' : [
        ['gifs', 'reddit_gifs'],
        ['AdviceAnimals', 'reddit_adviceanimals'],
    ],
}

# SITE PROFILES
# contains specific vars for site
reddit_profile = {
    'crop' : False, # set in for pixels to crop off the bottom of image.
    'allowed_sources' : ['i.imgur.com', 'i.redd.it'], # limit urls that we download from
    'sleep_seconds' : 10, # take a break between subreddits per https://github.com/reddit/reddit/wiki/API#rules 
}


