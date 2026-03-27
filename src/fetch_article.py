"""
Fetch complete metadata for a single OJS 2.4.5 article by its article_id.

This script connects to the database, retrieves all metadata for the specified article,
and saves a human-readable structured report to output/article_{article_id}.txt
or as JSON depending on the format option.

Usage:
    python src/fetch_article.py <article_id>
    python src/fetch_article.py <article_id> --format json
    python src/fetch_article.py <article_id> --output-dir /custom/output
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path to allow importing from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db_connector import get_connection
from tabulate import tabulate


def get_setting(settings_list, setting_name, locale=None):
    """Returns setting_value for given setting_name and optional locale."""
    for row in settings_list:
        if row['setting_name'] == setting_name:
            if locale is None or row.get('locale') == locale:
                return row['setting_value']
    return None


def get_settings_by_name(settings_list, setting_name):
    """Returns dict {locale: value} for all locales of given setting_name."""
    result = {}
    for row in settings_list:
        if row['setting_name'] == setting_name:
            result[row.get('locale', '')] = row['setting_value']
    return result


def convert_datetime(obj):
    """Convert datetime objects to ISO strings for JSON serialization."""
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def fetch_article_metadata(article_id):
    """
    Fetch complete metadata for a single article from the database.
    
    Args:
        article_id: The ID of the article to fetch
        
    Returns:
        Dictionary containing all article metadata
    """
    connection = None
    try:
        connection = get_connection()
        
        # Query 1 — Article core data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.article_id, a.locale, a.journal_id, a.section_id, a.language,
                       a.pages, a.date_submitted, a.last_modified, a.status, a.citations AS raw_citations_field
                FROM articles a
                WHERE a.article_id = %(article_id)s;
            """, {'article_id': article_id})
            article_result = cursor.fetchone()
            
            if not article_result:
                return None  # Article not found
            
            # Query 2 — Published article info (issue linkage)
            cursor.execute("""
                SELECT pa.published_article_id, pa.issue_id, pa.date_published, pa.seq
                FROM published_articles pa
                WHERE pa.article_id = %(article_id)s;
            """, {'article_id': article_id})
            published_result = cursor.fetchone()
            
            # Get journal_id and section_id from article result
            journal_id = article_result['journal_id']
            section_id = article_result['section_id']
            
            # Query 3 — Issue data (only if published)
            issue_result = None
            issue_id = None
            if published_result:
                issue_id = published_result['issue_id']
                cursor.execute("""
                    SELECT i.issue_id, i.journal_id, i.volume, i.number, i.year,
                           i.published, i.date_published AS issue_date_published,
                           i.date_notified
                    FROM issues i
                    WHERE i.issue_id = %(issue_id)s;
                """, {'issue_id': issue_id})
                issue_result = cursor.fetchone()
            
            # Query 4 — Issue settings (all locales)
            issue_settings = []
            if issue_id:
                cursor.execute("""
                    SELECT locale, setting_name, setting_value
                    FROM issue_settings
                    WHERE issue_id = %(issue_id)s
                    ORDER BY setting_name, locale;
                """, {'issue_id': issue_id})
                issue_settings = cursor.fetchall()
            
            # Query 5 — Journal data
            cursor.execute("""
                SELECT j.journal_id, j.path, j.primary_locale, j.enabled
                FROM journals j
                WHERE j.journal_id = %(journal_id)s;
            """, {'journal_id': journal_id})
            journal_result = cursor.fetchone()
            
            # Query 6 — Journal settings
            cursor.execute("""
                SELECT locale, setting_name, setting_value
                FROM journal_settings
                WHERE journal_id = %(journal_id)s
                  AND setting_name IN ('name', 'issn', 'printIssn', 'onlineIssn', 'abbreviation', 'publisherInstitution')
                ORDER BY setting_name, locale;
            """, {'journal_id': journal_id})
            journal_settings = cursor.fetchall()
            
            # Query 7 — Section data (only if section_id is not NULL)
            section_result = None
            section_settings = []
            if section_id:
                cursor.execute("""
                    SELECT s.section_id, s.journal_id, s.seq, s.hide_title
                    FROM sections s
                    WHERE s.section_id = %(section_id)s;
                """, {'section_id': section_id})
                section_result = cursor.fetchone()
                
                # Query 8 — Section settings
                if section_result:
                    cursor.execute("""
                        SELECT locale, setting_name, setting_value
                        FROM section_settings
                        WHERE section_id = %(section_id)s
                        ORDER BY setting_name, locale;
                    """, {'section_id': section_id})
                    section_settings = cursor.fetchall()
            
            # Query 9 — ALL article settings (all locales, all setting_names)
            cursor.execute("""
                SELECT locale, setting_name, setting_value
                FROM article_settings
                WHERE article_id = %(article_id)s
                ORDER BY setting_name, locale;
            """, {'article_id': article_id})
            article_settings = cursor.fetchall()
            
            # Query 10 — Authors (ordered by seq)
            cursor.execute("""
                SELECT author_id, seq, primary_contact,
                       first_name, middle_name, last_name,
                       email, country, url
                FROM authors
                WHERE submission_id = %(article_id)s
                ORDER BY seq ASC;
            """, {'article_id': article_id})
            authors = cursor.fetchall()
            
            # Query 11 — Author settings (ALL locales, ALL setting_names for each author)
            author_settings = []
            if authors:
                author_ids = [author['author_id'] for author in authors]
                if author_ids:  # Make sure we have author IDs
                    # Create placeholders for the IN clause
                    placeholders = ','.join(['%s'] * len(author_ids))
                    query = f"""
                        SELECT author_id, locale, setting_name, setting_value
                        FROM author_settings
                        WHERE author_id IN ({placeholders})
                        ORDER BY author_id, setting_name, locale;
                    """
                    cursor.execute(query, author_ids)
                    author_settings = cursor.fetchall()
            
            # Query 12 — Citations
            cursor.execute("""
                SELECT citation_id, seq, citation_state, raw_citation
                FROM citations
                WHERE assoc_type = 257 AND assoc_id = %(article_id)s
                ORDER BY seq ASC;
            """, {'article_id': article_id})
            citations = cursor.fetchall()
        
        # Check if article is published
        if not published_result:
            print(f"WARNING: Article {article_id} is not published (no entry in published_articles table)")
        
        # Assemble the article_data dictionary
        article_data = {
            "article_id": article_id,
            "article": article_result,
            "published_info": published_result,
            "issue": issue_result,
            "issue_settings": issue_settings,
            "journal": journal_result,
            "journal_settings": journal_settings,
            "section": section_result,
            "section_settings": section_settings,
            "article_settings": article_settings,
            "authors": authors,
            "author_settings": author_settings,
            "citations": citations,
        }
        
        return article_data
    
    finally:
        if connection:
            connection.close()


def format_txt_output(article_data):
    """
    Format the article data as a human-readable text report.
    
    Args:
        article_data: Dictionary containing all article metadata
        
    Returns:
        String with formatted text report
    """
    article_id = article_data['article_id']
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    output = f"""================================================================
OJS Article Metadata — article_id: {article_id}
Generated: {timestamp}
================================================================

## 1. ARTICLE (articles table)
article_id  : {article_data['article']['article_id']}
journal_id  : {article_data['article']['journal_id']}  → journal path: {article_data['journal']['path']}
section_id  : {article_data['article'].get('section_id', 'NULL')}
language    : {article_data['article'].get('language', 'N/A')}
pages       : {article_data['article'].get('pages', 'N/A')}
date_submitted : {article_data['article'].get('date_submitted', 'N/A')}
status      : {article_data['article'].get('status', 'N/A')}  (1=queued, 3=published, 4=declined)

## 2. PUBLICATION INFO
"""
    if article_data['published_info']:
        output += f"""published_article_id : {article_data['published_info']['published_article_id']}
issue_id    : {article_data['published_info']['issue_id']}
date_published : {article_data['published_info'].get('date_published', 'N/A')}
seq (order) : {article_data['published_info'].get('seq', 'N/A')}
"""
    else:
        output += "Article is not published (no entry in published_articles table)\n"
    
    output += "\n## 3. ISSUE\n"
    if article_data['issue']:
        output += f"""volume      : {article_data['issue'].get('volume', 'N/A')}
number      : {article_data['issue'].get('number', 'N/A')}
year        : {article_data['issue'].get('year', 'N/A')}
date_published : {article_data['issue'].get('issue_date_published', 'N/A')}
"""
    else:
        output += "No issue data (article not published)\n"
    
    output += "\n## 4. JOURNAL\n"
    output += f"""journal_id  : {article_data['journal']['journal_id']}
path        : {article_data['journal']['path']}
"""
    
    # Extract journal settings
    for setting in article_data['journal_settings']:
        output += f"{setting['setting_name']} ({setting['locale']}): {setting['setting_value']}\n"
    
    output += "\n## 5. SECTION\n"
    if article_data['section']:
        output += f"""section_id  : {article_data['section']['section_id']}
seq         : {article_data['section'].get('seq', 'N/A')}
hide_title  : {article_data['section'].get('hide_title', 'N/A')}
"""
        # Show section titles and abbreviations in different locales
        for setting in article_data['section_settings']:
            if setting['setting_name'] in ['title', 'abbrev']:
                output += f"{setting['setting_name']} ({setting['locale']}): {setting['setting_value']}\n"
    else:
        output += "(no section)\n"
    
    output += "\n## 6. ARTICLE SETTINGS (all fields, all locales)\n"
    if article_data['article_settings']:
        # Prepare data for tabulate
        table_data = []
        for setting in article_data['article_settings']:
            table_data.append([
                setting['setting_name'],
                setting['locale'],
                setting['setting_value']
            ])
        
        headers = ['setting_name', 'locale', 'setting_value']
        output += tabulate(table_data, headers=headers, tablefmt='grid') + "\n"
    else:
        output += "No article settings found.\n"
    
    output += "\n## 7. AUTHORS\n"
    if article_data['authors']:
        for i, author in enumerate(article_data['authors'], 1):
            output += f"""--- Author #{i} (author_id={author['author_id']}) ---
first_name    : {author.get('first_name', 'N/A')}
middle_name   : {author.get('middle_name', 'N/A')}
last_name     : {author.get('last_name', 'N/A')}
email         : {author.get('email', 'N/A')}
country       : {author.get('country', 'N/A')}
url           : {author.get('url', 'N/A')}
primary_contact: {author.get('primary_contact', 'N/A')}
  Settings:
"""
            # Find settings for this author
            author_specific_settings = [s for s in article_data['author_settings'] if s['author_id'] == author['author_id']]
            for setting in author_specific_settings:
                output += f"  {setting['setting_name']} ({setting['locale']}) : {setting['setting_value']}\n"
    else:
        output += "No authors found.\n"
    
    output += f"\n## 8. CITATIONS ({len(article_data['citations'])} total)\n"
    if article_data['citations']:
        for citation in article_data['citations']:
            output += f"[{citation['seq']}] {citation['raw_citation']}\n"
    else:
        output += "No citations found.\n"
    
    output += "\n## 9. MAPPING PREVIEW (OJS → journal3.xsd)\n"
    # Extract relevant data for mapping preview
    journal_issn = get_setting(article_data['journal_settings'], 'issn')
    journal_eissn = get_setting(article_data['journal_settings'], 'onlineIssn')
    journal_print_issn = get_setting(article_data['journal_settings'], 'printIssn')
    
    output += f"""<journal>
  issn    → {journal_print_issn or journal_issn}
  eissn   → {journal_eissn}
  <journalInfo lang="ru">
    <title> → {get_setting(article_data['journal_settings'], 'name', 'ru_RU') or '(missing)'}
  </journalInfo>
  <issue>
    <volume> → {article_data['issue']['volume'] if article_data['issue'] and article_data['issue'].get('volume') else '(empty)'}
    <number> → {article_data['issue']['number'] if article_data['issue'] else '(missing)'}
    <dateUni> → {article_data['issue']['year'] if article_data['issue'] else '(missing)'}
    <articles>
      <article>
        <langPubl> → {article_data['article'].get('language', 'N/A')}
        <pages>    → {article_data['article'].get('pages', 'N/A')}
        <artTitles>
          <artTitle lang="ru"> → {get_setting(article_data['article_settings'], 'title', 'ru_RU')[:80] if get_setting(article_data['article_settings'], 'title', 'ru_RU') else '(missing)'}
          <artTitle lang="en"> → {get_setting(article_data['article_settings'], 'title', 'en_US')[:80] if get_setting(article_data['article_settings'], 'title', 'en_US') else '(missing)'}
        </artTitles>
        <abstracts>
          <abstract lang="ru"> → {get_setting(article_data['article_settings'], 'abstract', 'ru_RU')[:150] if get_setting(article_data['article_settings'], 'abstract', 'ru_RU') else '(missing)'} [HTML: {'yes' if '<' in (get_setting(article_data['article_settings'], 'abstract', 'ru_RU') or '') else 'no'}]
          <abstract lang="en"> → {get_setting(article_data['article_settings'], 'abstract', 'en_US')[:150] if get_setting(article_data['article_settings'], 'abstract', 'en_US') else '(missing)'}
        </abstracts>
        <keywords>
          <kwdGroup lang="ru"> → {get_setting(article_data['article_settings'], 'subject', 'ru_RU').split(';') if get_setting(article_data['article_settings'], 'subject', 'ru_RU') else []}
        </keywords>
        <codes>
          <doi> → {get_setting(article_data['article_settings'], 'pub-id::doi') or '(missing)'}
        </codes>
        <authors> → {len(article_data['authors'])} authors
          [for each: surname, initials, orgName]
        <references> → {len(article_data['citations'])} citations
"""
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Fetch complete metadata for a single OJS 2.4.5 article")
    parser.add_argument('article_id', type=int, help='ID of the article to fetch')
    parser.add_argument('--output-dir', default='output', help='Output directory (default: output)')
    parser.add_argument('--format', choices=['txt', 'json'], default='txt', help='Output format (default: txt)')
    
    args = parser.parse_args()
    
    # Fetch the article metadata
    article_data = fetch_article_metadata(args.article_id)
    
    if not article_data:
        print(f"Error: Article with ID {args.article_id} not found in the database.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Determine output file path
    if args.format == 'json':
        output_path = os.path.join(args.output_dir, f'article_{args.article_id}.json')
        # Convert datetime objects to ISO strings for JSON serialization
        json_serializable_data = json.loads(json.dumps(article_data, default=convert_datetime))
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_serializable_data, f, ensure_ascii=False, indent=2)
    else:  # txt format
        output_path = os.path.join(args.output_dir, f'article_{args.article_id}.txt')
        txt_output = format_txt_output(article_data)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(txt_output)
    
    print(f"Metadata for article {args.article_id} saved to {output_path}")


if __name__ == "__main__":
    main()