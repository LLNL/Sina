# SinaWeb - DataModel Representation

This is a demo application to demonstrate a representation of the DataModel.
This application is meant as a proof-of-concept and not intended for 
production use.

# Getting Started

## Setting up a development environment (unix)

    python -m virtualenv venv
    source venv/bin/activate

## Setting up a development environment (windows)

    python -m virtualenv venv
    call venv/Scripts/activate.bat

## Install dependencies

    (venv) pip install -r requirements.txt

## Running the server

The Makefile (or for windows, make.bat) can be used to simplify the development. To run the database
migrations and start the server run:

    make all

This will apply any database migrations (keep the Django ORM models synced
with the SQLite database) and start the embedded Django development server.
Migrations will only be applied if you've made changes to `models.py`.

The default server for unix should be running on:
http://localhost:8000/

The default server for windows should be running on:
http://localhost:8080/

## Setting up a local admin account

Setting up an admin account is required to access the admin features in a local
development environment. The Django Tutorial describes how to set this up:
https://docs.djangoproject.com/en/1.11/intro/tutorial02/#introducing-the-django-admin

The admin site can be accessed via:
http://localhost:8000/admin
