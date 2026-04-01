import logging
import re
from lxml import etree
from src.db_connector import get_connection
from src.fetch_article import fetch_article_metadata, get_setting
from src.xml_generator import build_article_element


logger = logging.getLogger(__name__)


def fetch_issue_article_ids(issue_id: int) -> list[dict]:
    """
    Fetch the list of all published article IDs for a given issue_id from the DB.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
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
                'article_id': row[0],
                'seq': row[1],
                'section_id': row[2]
            })
        
        return result
    finally:
        cursor.close()
        conn.close()


def fetch_issue_metadata(issue_id: int) -> dict:
    """
    Fetch the issue row and its associated journal info.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Fetch issue data
        issue_query = """
            SELECT i.issue_id, i.journal_id, i.volume, i.number, i.year,
                   i.date_published
            FROM issues i
            WHERE i.issue_id = %s
        """
        cursor.execute(issue_query, (issue_id,))
        issue_row = cursor.fetchone()
        
        if not issue_row:
            raise ValueError(f"Issue with ID {issue_id} not found")
        
        issue_data = {
            'issue_id': issue_row[0],
            'journal_id': issue_row[1],
            'volume': issue_row[2],
            'number': issue_row[3],
            'year': issue_row[4],
            'date_published': issue_row[5]
        }
        
        # Fetch journal settings
        journal_query = """
            SELECT setting_name, locale, setting_value
            FROM journal_settings
            WHERE journal_id = %s
              AND setting_name IN ('printIssn', 'onlineIssn', 'name', 'publisherInstitution')
        """
        cursor.execute(journal_query, (issue_data['journal_id'],))
        journal_settings_rows = cursor.fetchall()
        
        # Process journal settings
        journal_settings = {}
        for row in journal_settings_rows:
            setting_name, locale, setting_value = row
            if setting_name not in journal_settings:
                journal_settings[setting_name] = {}
            journal_settings[setting_name][locale] = setting_value
        
        # Extract specific values
        issue_data['print_issn'] = journal_settings.get('printIssn', {}).get('', '')
        issue_data['online_issn'] = journal_settings.get('onlineIssn', {}).get('', '')
        issue_data['title_ru'] = journal_settings.get('name', {}).get('ru_RU', '')
        issue_data['title_en'] = journal_settings.get('name', {}).get('en_US', '')
        issue_data['publisher'] = journal_settings.get('publisherInstitution', {}).get('', '')
        
        return issue_data
    finally:
        cursor.close()
        conn.close()


def compute_issue_pages(articles_data):
    """
    Compute the total page range of the issue from all article pages.
    """
    fpages = []
    lpages = []
    
    for article_data in articles_data:
        article_info = article_data.get('article', {})
        pages_str = article_info.get('pages', '')
        
        if not pages_str:
            continue
        
        # Normalize dashes
        normalized_pages = pages_str.replace('\u2013', '-').replace('\u2014', '-')
        
        # Extract fpage and lpage
        parts = normalized_pages.split('-')
        if len(parts) >= 2:
            try:
                fpage = int(parts[0].strip())
                lpage = int(parts[1].strip())
                fpages.append(fpage)
                lpages.append(lpage)
            except ValueError:
                # Skip if conversion to int fails
                continue
        elif len(parts) == 1:
            try:
                fpage = int(parts[0].strip())
                fpages.append(fpage)
                lpages.append(fpage)  # Single page
            except ValueError:
                # Skip if conversion to int fails
                continue
    
    if not fpages or not lpages:
        return ''
    
    return f"{min(fpages)}-{max(lpages)}"


def get_section_titles(section_id: int):
    """
    Fetch section titles for a given section_id.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT setting_name, locale, setting_value
            FROM section_settings
            WHERE section_id = %s
              AND setting_name IN ('title', 'abbrev')
        """
        cursor.execute(query, (section_id,))
        rows = cursor.fetchall()
        
        titles = {}
        for row in rows:
            setting_name, locale, setting_value = row
            if setting_name not in titles:
                titles[setting_name] = {}
            titles[setting_name][locale] = setting_value
        
        # Extract title_ru and title_en
        title_ru = titles.get('title', {}).get('ru_RU', '')
        title_en = titles.get('title', {}).get('en_US', '')
        
        return {'title_ru': title_ru, 'title_en': title_en}
    finally:
        cursor.close()
        conn.close()


def build_journal_xml(issue_id: int, titleid: str = ''):
    """
    Main function to build the complete journal XML tree.
    """
    # Fetch issue metadata
    issue_metadata = fetch_issue_metadata(issue_id)
    
    # Fetch article IDs for the issue
    article_ids = fetch_issue_article_ids(issue_id)
    
    # Fetch metadata for each article
    articles_data = []
    for i, article_info in enumerate(article_ids, 1):
        article_id = article_info['article_id']
        logger.info(f"Processing article {article_id} ({i}/{len(article_ids)})...")
        
        try:
            article_data = fetch_article_metadata(article_id)
            if article_data is not None:
                articles_data.append(article_data)
            else:
                logger.warning(f"Article {article_id} returned None from fetch_article_metadata")
        except Exception as e:
            logger.error(f"Error fetching metadata for article {article_id}: {e}")
            continue  # Skip this article and continue with others
    
    # Create the root element
    root = etree.Element('journal')
    
    # Add titleid
    titleid_elem = etree.SubElement(root, 'titleid')
    titleid_elem.text = titleid
    
    # Add issn
    issn_elem = etree.SubElement(root, 'issn')
    issn_elem.text = issue_metadata.get('print_issn', '')
    
    # Add eissn
    eissn_elem = etree.SubElement(root, 'eissn')
    eissn_elem.text = issue_metadata.get('online_issn', '')
    
    # Add journalInfo in Russian
    journal_info_ru = etree.SubElement(root, 'journalInfo')
    journal_info_ru.set('lang', 'ru')
    
    title_ru_elem = etree.SubElement(journal_info_ru, 'title')
    title_ru_elem.text = issue_metadata.get('title_ru', '')
    
    publ_ru_elem = etree.SubElement(journal_info_ru, 'publ')
    publ_ru_elem.text = issue_metadata.get('publisher', '')
    
    # Add journalInfo in English
    journal_info_en = etree.SubElement(root, 'journalInfo')
    journal_info_en.set('lang', 'en')
    
    title_en_elem = etree.SubElement(journal_info_en, 'title')
    title_en_elem.text = issue_metadata.get('title_en', '')
    
    publ_en_elem = etree.SubElement(journal_info_en, 'publ')
    publ_en_elem.text = issue_metadata.get('publisher', '')
    
    # Add issue element
    issue_elem = etree.SubElement(root, 'issue')
    
    # Add volume
    volume = issue_metadata.get('volume', '')
    volume_elem = etree.SubElement(issue_elem, 'volume')
    volume_elem.text = str(volume) if volume and str(volume) != '0' else ''
    
    # Add number
    number = issue_metadata.get('number', '')
    number_elem = etree.SubElement(issue_elem, 'number')
    number_elem.text = str(number) if number else ''
    
    # Add dateUni (year)
    year = issue_metadata.get('year', '')
    date_uni_elem = etree.SubElement(issue_elem, 'dateUni')
    date_uni_elem.text = str(year) if year else ''
    
    # Add pages
    computed_issue_pages = compute_issue_pages(articles_data)
    pages_elem = etree.SubElement(issue_elem, 'pages')
    pages_elem.text = computed_issue_pages
    
    # Add articles container
    articles_container = etree.SubElement(issue_elem, 'articles')
    
    # Group articles by section and build XML
    processed_sections = set()
    current_section_id = None
    
    for article_data in articles_data:
        article_info = article_data.get('article', {})
        section_id = article_info.get('section_id')
        
        # If we're moving to a new section, add the section element
        if section_id != current_section_id:
            if section_id not in processed_sections:
                # Get section titles
                section_titles = get_section_titles(section_id)
                title_ru = section_titles.get('title_ru', '')
                title_en = section_titles.get('title_en', '')
                
                # Only add section if we have titles
                if title_ru or title_en:
                    section_elem = etree.SubElement(articles_container, 'section')
                    
                    if title_ru:
                        sec_title_ru = etree.SubElement(section_elem, 'secTitle')
                        sec_title_ru.set('lang', 'ru')
                        sec_title_ru.text = title_ru
                    
                    if title_en:
                        sec_title_en = etree.SubElement(section_elem, 'secTitle')
                        sec_title_en.set('lang', 'en')
                        sec_title_en.text = title_en
                
                processed_sections.add(section_id)
            
            current_section_id = section_id
        
        # Build article element
        article_element = build_article_element(article_data)
        if article_element is not None:
            articles_container.append(article_element)
    
    # Log summary
    n_articles = len(articles_data)
    n_sections = len(processed_sections)
    logger.info(f"Built XML for issue {issue_id}: {n_articles} articles, {n_sections} sections.")
    
    # Return the complete tree
    tree = etree.ElementTree(root)
    return tree