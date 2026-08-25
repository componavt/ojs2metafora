"""
OJS 2.4 adapter implementation.

This module contains the Ojs24Adapter class that implements database access
for OJS 2.4.5 metadata extraction.
"""
from typing import Dict, List, Any
from src.adapters.base import OjsAdapter
from src.db_connector import get_connection


class Ojs24Adapter(OjsAdapter):
    """
    Adapter for OJS 2.4.5 database schema.
    
    Implements the OjsAdapter contract for fetching article, issue, and section
    metadata from OJS 2.4.5 databases.
    """
    
    def fetch_article_metadata(self, article_id: int) -> Dict[str, Any]:
        """
        Fetch complete metadata for a single article.
        
        Args:
            article_id: The ID of the article to fetch.
        
        Returns:
            Dictionary containing all article metadata with keys:
            article_id, article, published_info, issue, issue_settings,
            journal, journal_settings, section, section_settings,
            article_settings, authors, author_settings, citations.
        """
        connection = get_connection(self.source_key)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT a.article_id, a.locale, a.journal_id, a.section_id, a.language,
                           a.pages, a.date_submitted, a.last_modified, a.status, a.citations AS raw_citations_field
                    FROM articles a
                    WHERE a.article_id = %(article_id)s;
                """, {'article_id': article_id})
                article_result = cursor.fetchone()
                
                if not article_result:
                    return None
                
                published_result = None
                issue_result = None
                issue_id = None
                journal_id = article_result['journal_id']
                section_id = article_result['section_id']
                
                cursor.execute("""
                    SELECT pa.published_article_id, pa.issue_id, pa.date_published, pa.seq
                    FROM published_articles pa
                    WHERE pa.article_id = %(article_id)s;
                """, {'article_id': article_id})
                published_result = cursor.fetchone()
                
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
                
                issue_settings = []
                if issue_id:
                    cursor.execute("""
                        SELECT locale, setting_name, setting_value
                        FROM issue_settings
                        WHERE issue_id = %(issue_id)s
                        ORDER BY setting_name, locale;
                    """, {'issue_id': issue_id})
                    issue_settings = cursor.fetchall()
                
                cursor.execute("""
                    SELECT j.journal_id, j.path, j.primary_locale, j.enabled
                    FROM journals j
                    WHERE j.journal_id = %(journal_id)s;
                """, {'journal_id': journal_id})
                journal_result = cursor.fetchone()
                
                cursor.execute("""
                    SELECT locale, setting_name, setting_value
                    FROM journal_settings
                    WHERE journal_id = %(journal_id)s
                      AND setting_name IN ('name', 'issn', 'printIssn', 'onlineIssn', 'abbreviation', 'publisherInstitution')
                    ORDER BY setting_name, locale;
                """, {'journal_id': journal_id})
                journal_settings = cursor.fetchall()
                
                section_result = None
                section_settings = []
                if section_id:
                    cursor.execute("""
                        SELECT s.section_id, s.journal_id, s.seq, s.hide_title
                        FROM sections s
                        WHERE s.section_id = %(section_id)s;
                    """, {'section_id': section_id})
                    section_result = cursor.fetchone()
                    
                    if section_result:
                        cursor.execute("""
                            SELECT locale, setting_name, setting_value
                            FROM section_settings
                            WHERE section_id = %(section_id)s
                            ORDER BY setting_name, locale;
                        """, {'section_id': section_id})
                        section_settings = cursor.fetchall()
                
                cursor.execute("""
                    SELECT locale, setting_name, setting_value
                    FROM article_settings
                    WHERE article_id = %(article_id)s
                    ORDER BY setting_name, locale;
                """, {'article_id': article_id})
                article_settings = cursor.fetchall()
                
                cursor.execute("""
                    SELECT author_id, seq, primary_contact,
                           first_name, middle_name, last_name,
                           email, country, url
                    FROM authors
                    WHERE submission_id = %(article_id)s
                    ORDER BY seq ASC;
                """, {'article_id': article_id})
                authors = cursor.fetchall()
                
                author_settings = []
                if authors:
                    author_ids = [author['author_id'] for author in authors]
                    if author_ids:
                        placeholders = ','.join(['%s'] * len(author_ids))
                        query = f"""
                            SELECT author_id, locale, setting_name, setting_value
                            FROM author_settings
                            WHERE author_id IN ({placeholders})
                            ORDER BY author_id, setting_name, locale;
                        """
                        cursor.execute(query, author_ids)
                        author_settings = cursor.fetchall()
                
                cursor.execute("""
                    SELECT citation_id, seq, citation_state, raw_citation
                    FROM citations
                    WHERE assoc_type = 257 AND assoc_id = %(article_id)s
                    ORDER BY seq ASC;
                """, {'article_id': article_id})
                citations = cursor.fetchall()
        
        finally:
            connection.close()
        
        if not published_result:
            print(f"WARNING: Article {article_id} is not published (no entry in published_articles table)")
        
        return {
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
    
    def fetch_issue_article_ids(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all published article IDs for a given issue.
        
        Args:
            issue_id: The ID of the issue.
        
        Returns:
            List of dictionaries with keys: article_id, seq, section_id.
        """
        connection = get_connection(self.source_key)
        try:
            with connection.cursor() as cursor:
                query = """
                    SELECT
                        pa.article_id,
                        pa.seq,
                        a.section_id
                    FROM published_articles pa
                    JOIN articles a ON a.article_id = pa.article_id
                    WHERE pa.issue_id = %s
                      AND a.status = 3
                    ORDER BY pa.seq ASC
                """
                cursor.execute(query, (issue_id,))
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    result.append({
                        'article_id': row['article_id'],
                        'seq': row['seq'],
                        'section_id': row['section_id']
                    })
                
                return result
        finally:
            connection.close()
    
    def fetch_issue_metadata(self, issue_id: int) -> Dict[str, Any]:
        """
        Fetch issue and journal metadata for a given issue.
        
        Args:
            issue_id: The ID of the issue.
        
        Returns:
            Dictionary containing issue and journal metadata with keys:
            issue_id, journal_id, volume, number, year, date_published,
            print_issn, online_issn, title_ru, title_en, publisher, journal_path.
        """
        connection = get_connection(self.source_key)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT i.issue_id, i.journal_id, i.volume, i.number, i.year,
                           i.date_published
                    FROM issues i
                    WHERE i.issue_id = %s
                """, (issue_id,))
                issue_row = cursor.fetchone()
                
                if not issue_row:
                    raise ValueError(f"Issue with ID {issue_id} not found")
                
                issue_data = {
                    'issue_id': issue_row['issue_id'],
                    'journal_id': issue_row['journal_id'],
                    'volume': issue_row['volume'],
                    'number': issue_row['number'],
                    'year': issue_row['year'],
                    'date_published': issue_row['date_published']
                }
                
                cursor.execute("""
                    SELECT path FROM journals WHERE journal_id = %s
                """, (issue_data['journal_id'],))
                journal_path_row = cursor.fetchone()
                issue_data['journal_path'] = journal_path_row['path'] if journal_path_row else ''
                
                cursor.execute("""
                    SELECT setting_name, locale, setting_value
                    FROM journal_settings
                    WHERE journal_id = %s
                      AND setting_name IN ('printIssn', 'onlineIssn', 'name', 'publisherInstitution')
                """, (issue_data['journal_id'],))
                journal_settings_rows = cursor.fetchall()
                
                journal_settings = {}
                for row in journal_settings_rows:
                    setting_name = row['setting_name']
                    locale = row['locale']
                    setting_value = row['setting_value']
                    if setting_name not in journal_settings:
                        journal_settings[setting_name] = {}
                    journal_settings[setting_name][locale] = setting_value
                
                issue_data['print_issn'] = journal_settings.get('printIssn', {}).get('', '')
                issue_data['online_issn'] = journal_settings.get('onlineIssn', {}).get('', '')
                issue_data['title_ru'] = journal_settings.get('name', {}).get('ru_RU', '')
                issue_data['title_en'] = journal_settings.get('name', {}).get('en_US', '')
                issue_data['publisher'] = journal_settings.get('publisherInstitution', {}).get('', '')
                
                return issue_data
        finally:
            connection.close()
    
    def get_section_titles(self, section_id: int) -> Dict[str, str]:
        """
        Fetch titles for a given section.
        
        Args:
            section_id: The ID of the section.
        
        Returns:
            Dictionary with keys: title_ru, title_en.
        """
        connection = get_connection(self.source_key)
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT setting_name, locale, setting_value
                    FROM section_settings
                    WHERE section_id = %s
                      AND setting_name IN ('title', 'abbrev')
                """, (section_id,))
                rows = cursor.fetchall()
                
                titles = {}
                for row in rows:
                    setting_name = row['setting_name']
                    locale = row['locale']
                    setting_value = row['setting_value']
                    if setting_name not in titles:
                        titles[setting_name] = {}
                    titles[setting_name][locale] = setting_value
                
                title_ru = titles.get('title', {}).get('ru_RU', '')
                title_en = titles.get('title', {}).get('en_US', '')
                
                return {'title_ru': title_ru, 'title_en': title_en}
        finally:
            connection.close()
