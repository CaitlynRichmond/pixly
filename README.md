# Pix.ly - Simple Image Editing
Pix.ly is a simple image editing program. It's built as a multi-page web application with
server-side rendering with Jinja. The goal of this project was to be given a project idea and four days to implement on it.

View the deployed site [here](https://pixly.onrender.com/), deployed with Render.

Render can take a few minutes to spin up


<b>Prompt:</b>

    (Login/authentication isn’t required; any web user can do everything)

    Users can view photos stored in the system

    Users can add a JPG photo using an upload form and picking a file on their computer

    System will retrieve metadata from the photo (location of photo, model of camera, etc) and store it into the database

    Images themselves are stored to Amazon S3, not in the database

    Users can search image data from the EXIF fields (you can learn about PostgreSQL full-text search)

    Users can perform simple image edits

## Tech Stack
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Postgres](https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white)
![Jinja](https://img.shields.io/badge/jinja-white.svg?style=for-the-badge&logo=jinja&logoColor=black)

## Features
Here is an overview of some of the key features

- Image uploads supports .webp, .png, .heic, .jpeg, and .jpg.
- Files are stored on AWS S3 with metadata, when present, being stored in the data base along with user-provided caption, title, and attribution field.
- The search searches by caption, title, and by fields of the photos
- On the gallery page, can filter by images with metadata for make and model of the camera that took the picture
- On image specific page, several image operations using the Pillow library can be applied to the image. Images can also be reverted, or completely deleted.

## Local setup instructions
Fork and clone this repo

from the root folder of your forked repo

1.) Create the virtual environment and install the requirements using the following terminal commands:
```
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```
2.) Set up your local database (this assumes you have Postgres installed, if not, you can find instructions [here](https://www.postgresql.org/download/)

```
psql
CREATE DATABASE pixly;
(ctrl+D)
python3 seed.py
```
3.) Setup environment variables in .env
- create a .env file at the root of the project
- copy and paste the following code into your new .env file
  ```
  SECRET_KEY=secret
  DATABASE_URL=postgresql:///pixly
  AWS_BUCKET=[your bucket here]
  AWS_ACCESS_KEY=[your access key here]
  AWS_SECRET_KEY=[your secret key here]
  ```

4.) Run the development server.
```
flask run -p 5001
```
Flask defaults to port 5000, however, many MacOS devices use port 5000 for airplay.

Pix.ly will now be viewable on localhost:5001



## Acknowledgements
Pix.ly was built during my time at Rithm School, as part of a 4-day solo sprint.