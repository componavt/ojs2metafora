"""
Database connector module for OJS 2.4.5 database.

This module provides a function to establish a connection to the MySQL database
containing OJS 2.4.5 data using credentials from the .env file.
"""

import os
from dotenv import load_dotenv
import pymysql

# Load environment variables from .env file
load_dotenv()


def get_connection():
    """
    Creates and returns a MySQL database connection using credentials from .env file.
    
    Returns:
        pymysql.Connection: A connection object configured with DictCursor for 
        dictionary-style row access.
    """
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        charset=os.getenv('DB_CHARSET', 'utf8mb4'),
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection