"""
Database exploration script for OJS 2.4.5 database.

This script connects to a local MySQL database containing an OJS 2.4.5 dump,
extracts 2-3 sample rows from each key table, anonymizes personal data,
and saves a human-readable report to output/db_sample.txt.

Usage:
    python src/explore_db.py
    (run from the project root directory)
"""

import os
import sys
import datetime
from tabulate import tabulate

# Add the project root to the Python path to allow importing from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db_connector import get_connection


def anonymize_authors_data(rows):
    """
    Anonymizes personal data in authors table results.
    
    Args:
        rows: List of dictionaries representing author records
        
    Returns:
        List of anonymized author records
    """
    anonymized_rows = []
    counter = 1
    
    for row in rows:
        new_row = row.copy()
        # Anonymize personal data fields if they exist in the row
        if 'first_name' in new_row:
            new_row['first_name'] = f"Имя{counter}"
        if 'last_name' in new_row:
            new_row['last_name'] = f"Фамилия{counter}"
        if 'middle_name' in new_row:
            new_row['middle_name'] = f"Отчество{counter}"
        if 'email' in new_row:
            new_row['email'] = f"email{counter}@example.com"
        anonymized_rows.append(new_row)
        counter += 1
    
    return anonymized_rows


def anonymize_author_settings_data(rows):
    """
    Anonymizes personal data in author_settings table results.
    
    Args:
        rows: List of dictionaries representing author settings records
        
    Returns:
        List of anonymized author settings records
    """
    anonymized_rows = []
    
    for row in rows:
        new_row = row.copy()
        if row.get('setting_name') == 'biography':
            new_row['setting_value'] = '[biography hidden]'
        anonymized_rows.append(new_row)
    
    return anonymized_rows


def run_query_and_format(connection, query, title, anonymize_func=None):
    """
    Executes a query, optionally anonymizes the results, and formats them.
    
    Args:
        connection: Database connection object
        query: SQL query string to execute
        title: Title to display for this query result
        anonymize_func: Optional function to anonymize the results
        
    Returns:
        Formatted string representation of the query results
    """
    with connection.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()
        
        if anonymize_func:
            results = anonymize_func(results)
        
        if results:
            headers = list(results[0].keys())
            rows = [list(row.values()) for row in results]
            table_str = tabulate(rows, headers=headers, tablefmt='grid')
        else:
            table_str = "No results found."
        
        return f"\n[{title}] {query.split('FROM')[0].split()[-1].upper()} ({len(results)} rows)\n" \
               f"------------------------------------------------------------\n" \
               f"{table_str}\n"


def main():
    """
    Main function to connect to the database, run queries, and generate the report.
    """
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Establish database connection
    connection = None
    try:
        connection = get_connection()
        
        # Define the queries to run
        queries = [
            ("A", "SELECT issue_id, journal_id, volume, number, year, published, date_published FROM issues WHERE published = 1 ORDER BY issue_id DESC LIMIT 3;", None),
            ("B", "SELECT issue_id, locale, setting_name, setting_value FROM issue_settings WHERE setting_name = 'title' ORDER BY issue_id DESC LIMIT 6;", None),
            ("C", "SELECT pa.published_article_id, pa.article_id, pa.issue_id, pa.date_published, pa.seq FROM published_articles pa ORDER BY pa.issue_id DESC, pa.seq ASC LIMIT 5;", None),
            ("D", "SELECT article_id, locale, journal_id, section_id, language, pages, date_submitted, status FROM articles ORDER BY article_id DESC LIMIT 3;", None),
            ("E", "SELECT DISTINCT setting_name, locale FROM article_settings ORDER BY setting_name, locale LIMIT 60;", None),
            ("F", "SELECT article_id, locale, setting_name, LEFT(setting_value, 120) AS setting_value FROM article_settings WHERE setting_name IN ('title', 'abstract', 'subject', 'discipline', 'coverageGeo', 'type') ORDER BY article_id DESC, setting_name, locale LIMIT 20;", None),
            ("G", "SELECT author_id, submission_id, first_name, middle_name, last_name, email, seq, primary_contact, country FROM authors ORDER BY author_id DESC LIMIT 5;", anonymize_authors_data),
            ("H", "SELECT author_id, locale, setting_name, LEFT(setting_value, 80) AS setting_value FROM author_settings WHERE setting_name IN ('affiliation', 'biography') ORDER BY author_id DESC LIMIT 10;", anonymize_author_settings_data),
            ("I", "SELECT s.section_id, s.journal_id, ss.locale, ss.setting_name, ss.setting_value FROM sections s JOIN section_settings ss ON s.section_id = ss.section_id WHERE ss.setting_name IN ('title', 'abbrev') ORDER BY s.section_id, ss.locale LIMIT 20;", None),
            ("J", "SELECT citation_id, assoc_type, assoc_id, citation_state, seq, LEFT(raw_citation, 150) AS raw_citation FROM citations ORDER BY assoc_id DESC, seq ASC LIMIT 5;", None),
            ("K", "SELECT journal_id, locale, setting_name, setting_value FROM journal_settings WHERE setting_name IN ('name', 'issn', 'printIssn', 'onlineIssn', 'abbreviation') ORDER BY journal_id, setting_name, locale;", None),
            ("L", "SELECT journal_id, path, primary_locale, enabled FROM journals;", None),
        ]
        
        # Generate the report
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_content = f"""============================================================
OJS Database Sample — generated: {timestamp}
============================================================

"""
        
        for title, query, anonymize_func in queries:
            print(f"Running query {title}...")
            report_content += run_query_and_format(connection, query, title, anonymize_func)
        
        # Write the report to output file
        output_path = "output/db_sample.txt"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"\nReport generated successfully: {output_path}")
        print(f"Total queries executed: {len(queries)}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise
    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    main()