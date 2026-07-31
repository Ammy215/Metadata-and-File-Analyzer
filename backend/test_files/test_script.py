
import os
import sys

# Suspicious patterns
password = "admin123"
api_key = "sk-1234567890abcdef"
database_url = "mysql://root:password@localhost/db"

def connect_database():
    return database_url
