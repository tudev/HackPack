'''
    config.py
    Configuration module for the server
'''

import os
basedir = os.path.abspath(os.path.dirname(__file__))

from uuid import uuid5, NAMESPACE_DNS
from socket import gethostname


class Config:
    def __init__(self):
        pass

    CLIENT_ID = uuid5(NAMESPACE_DNS, gethostname())
    VERSION = "1.1"
    AUTHOR = "Jake Lawrence"
    NAME = "Checkout"
    HOSTNAME = gethostname()

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(Config):
    CONFIG_DIR = '/var/log/'
    DEBUG = True
    LOGLEVEL = DEBUG
    DB_USER = os.getenv('DB_USER')
    DB_PASS = os.getenv('DB_PASS')
    SLACK_KEY = os.getenv('SLACK_KEY')
    CLIENT_ID = os.getenv('CLIENT_ID')
    CLIENT_SECRET = os.getenv('CLIENT_SECRET')
    ADMIN_EMAILS = ['tug64918@temple.edu', 'tug86304@temple.edu',
                    'tug37553@temple.edu', 'tuf01128@temple.edu']
    WELCOME_MSG = ['Welcome, ', 'Time to Hack, ', 'Hey there, ']
    REQUEST_EMAIL_SEND = 'tudev.hardware@temple.edu'
    REQUEST_EMAIL_ADMINS = ['tug64918@temple.edu']
    SMTP = 'smtp.gmail.com:587'
    EMAIL_USER = os.getenv('EMAIL_USER')
    EMAIL_PASS = os.getenv('EMAIL_PASS')


config = {
    'default': ProductionConfig
}
