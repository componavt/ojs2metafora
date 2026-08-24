"""
Database connector module for OJS databases.

This module provides a function to establish a connection to the MySQL database
containing OJS data using credentials from the .env file.
"""

import os
from dotenv import load_dotenv
import pymysql

from .sources import SOURCES

load_dotenv()


def get_connection(source_key: str = "karrc"):
    """
    Creates and returns a MySQL database connection for the specified source.
    
    Args:
        source_key: The key identifying the source configuration (default: "karrc").
    
    Returns:
        pymysql.Connection: A connection object configured with DictCursor for 
        dictionary-style row access.
    
    Raises:
        ValueError: If source_key is unknown or required configuration is missing.
    """
    if source_key not in SOURCES:
        available = ", ".join(sorted(SOURCES.keys()))
        raise ValueError(
            f"Unknown source key '{source_key}'. Available sources: {available}"
        )
    
    profile = SOURCES[source_key]
    env_prefix = profile["env_prefix"]
    
    dbhost = os.getenv(f"{env_prefix}_DBHOST", "").strip()
    dbuser = os.getenv(f"{env_prefix}_DBUSER", "").strip()
    dbpassword = os.getenv(f"{env_prefix}_DBPASSWORD", "")
    dbname = os.getenv(f"{env_prefix}_DBNAME", "").strip()
    dbcharset = os.getenv(f"{env_prefix}_DBCHARSET", "").strip()
    
    if not dbhost:
        raise ValueError(
            f"Missing required configuration: {env_prefix}_DBHOST is not set"
        )
    if not dbuser:
        raise ValueError(
            f"Missing required configuration: {env_prefix}_DBUSER is not set"
        )
    if not dbname:
        raise ValueError(
            f"Missing required configuration: {env_prefix}_DBNAME is not set"
        )
    
    if not dbcharset:
        dbcharset = "utf8mb4"
    
    connection = pymysql.connect(
        host=dbhost,
        user=dbuser,
        password=dbpassword,
        database=dbname,
        charset=dbcharset,
        cursorclass=pymysql.cursors.DictCursor
    )
    return connection