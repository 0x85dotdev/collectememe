## collectememe
Crawl Reddit via their public API endpoints to grab and process defined files types.

### Features
* Optionally, if video/MP4 files are processed, an associated screenshot will be processed using FFMPEG.
* Keep files local or upload to S3
* As files are downloaded, MD5 checksums are stored in a database and used to ensure duplicate files are not stored
* Use config to profile what to pull, where from, and customize to your desire

### Requirements
* Python > 3.5
* FFMPEG (if processing video/mp4 MIME)
* MySQL
* various Python libraries in requirements.txt
* if using S3 you will need aws-cli

ssh access to willing servers

### Usage
Make sure you install dependencies from requirements.txt
```
python schema.py
python crawl.py
```

### TODO
* add image cropping options
* use FFMPEG to convert image/gif to video/mp4
* make mp4 screenshot optional
* clean up janky bits