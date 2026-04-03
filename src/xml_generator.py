import re
import logging
from lxml import etree
from itertools import zip_longest
from typing import Optional
from fetch_article import get_setting, get_settings_by_name


logger = logging.getLogger(__name__)


def clean_html(text: str) -> str:
    """Strip HTML tags from abstract/bio text."""
    if not text:
        return ''
    return re.sub(r'<[^>]+>', '', text).strip()


def parse_pages(pages_str: str) -> str:
    """Normalize page range: replace en-dash/em-dash with regular hyphen."""
    if not pages_str:
        return ''
    return pages_str.replace('\u2013', '-').replace('\u2014', '-').strip()


def extract_doi(settings, setting_name='pub-id::doi') -> str:
    """Extract DOI value from article_settings."""
    return get_setting(settings, setting_name) or ''


def is_cyrillic(name: str) -> bool:
    """Check if a name contains Cyrillic characters."""
    return bool(re.search(r'[А-Яа-яЁё]', name))


def parse_keywords(subject_str: str) -> list:
    """Parse semicolon-separated keywords."""
    if not subject_str:
        return []
    return [kw.strip() for kw in subject_str.split(';') if kw.strip()]


def _fmt_date(val):
    """Return YYYY-MM-DD string from date/datetime/string, or None if falsy."""
    if not val:
        return None
    if hasattr(val, 'strftime'):
        return val.strftime('%Y-%m-%d')
    s = str(val)
    return s[:10] if len(s) >= 10 else s


def build_article_element(article_data: dict):
    """
    Build and return a single <article> lxml Element from article_data.
    Returns None if article_data is None or article is not published (status != 3).
    """
    if not article_data:
        return None
    
    article = article_data.get('article', {})
    
    # Check if article is published (status == 3)
    if article.get('status') != 3:
        return None
    
    # Create the root article element
    article_elem = etree.Element('article')
    
    # Add language publication
    language = article.get('language', '')
    if language:
        lang_publ_elem = etree.SubElement(article_elem, 'langPubl')
        lang_publ_elem.text = language[:2]  # Take first 2 characters (e.g., "ru", "en")
    
    # Add pages
    pages = article.get('pages', '')
    if pages:
        pages_elem = etree.SubElement(article_elem, 'pages')
        pages_elem.text = parse_pages(pages)
    
    # Add codes (DOI)
    doi = extract_doi(article_data.get('article_settings', []))
    if doi:
        codes_elem = etree.SubElement(article_elem, 'codes')
        doi_elem = etree.SubElement(codes_elem, 'doi')
        doi_elem.text = doi
    
    # Process authors
    authors_elem = etree.SubElement(article_elem, 'authors')
    
    # Get authors and sort by seq
    all_authors = article_data.get('authors', [])
    sorted_authors = sorted(all_authors, key=lambda x: x['seq'])
    
    # Split authors into Russian and English based on Cyrillic detection
    ru_authors = [a for a in sorted_authors if is_cyrillic(a['last_name'])]
    en_authors = [a for a in sorted_authors if not is_cyrillic(a['last_name'])]
    
    # Pair authors by position
    author_pairs = zip_longest(ru_authors, en_authors, fillvalue=None)
    
    # Convert flat list [{author_id, locale, setting_name, setting_value}, ...]
    # to nested dict {author_id: {setting_name: {locale: value}}}
    author_settings_raw = article_data.get('author_settings', [])
    author_settings = {}
    for _row in author_settings_raw:
        _aid  = _row['author_id']
        _name = _row['setting_name']
        _loc  = _row.get('locale') or ''
        _val  = _row.get('setting_value') or ''
        if _aid not in author_settings:
            author_settings[_aid] = {}
        if _name not in author_settings[_aid]:
            author_settings[_aid][_name] = {}
        author_settings[_aid][_name][_loc] = _val
    
    for idx, (ru_author, en_author) in enumerate(author_pairs, 1):
        # Determine which author ID to use for the author element
        author_id = ru_author['author_id'] if ru_author else en_author['author_id']
        
        # Create author element
        author_elem = etree.SubElement(authors_elem, 'author')
        author_elem.set('num', str(idx))
        author_elem.set('id', str(author_id))
        
        # Add Russian individInfo if available
        if ru_author:
            ru_individ_info = etree.SubElement(author_elem, 'individInfo')
            ru_individ_info.set('lang', 'ru')
            
            # Surname in uppercase
            surname_elem = etree.SubElement(ru_individ_info, 'surname')
            surname_elem.text = ru_author['last_name'].upper()
            
            # Initials: first_name + middle_name if present
            initials_text = ru_author['first_name']
            if ru_author.get('middle_name'):
                initials_text += " " + ru_author['middle_name']
            initials_elem = etree.SubElement(ru_individ_info, 'initials')
            initials_elem.text = initials_text
            
            # Organization name (affiliation in Russian)
            ru_affiliation = author_settings.get(ru_author['author_id'], {}).get('affiliation', {})
            if isinstance(ru_affiliation, dict):
                org_name = ru_affiliation.get('ru_RU', '')
            else:
                org_name = ru_affiliation
            if org_name:
                org_elem = etree.SubElement(ru_individ_info, 'orgName')
                org_elem.text = org_name
            
            # Email
            email_elem = etree.SubElement(ru_individ_info, 'email')
            email_elem.text = ru_author.get('email', '')
            
            # Biography in Russian
            ru_bio = author_settings.get(ru_author['author_id'], {}).get('biography', {})
            if isinstance(ru_bio, dict):
                bio_text = ru_bio.get('ru_RU', '')
            else:
                bio_text = ru_bio
            if bio_text:
                bio_elem = etree.SubElement(ru_individ_info, 'bio')
                bio_elem.text = clean_html(bio_text)
        
        # Add English individInfo if available
        if en_author:
            en_individ_info = etree.SubElement(author_elem, 'individInfo')
            en_individ_info.set('lang', 'en')
            
            # Surname in uppercase
            surname_elem = etree.SubElement(en_individ_info, 'surname')
            surname_elem.text = en_author['last_name'].upper()
            
            # Initials: first_name + middle_initial if middle_name is present
            initials_text = en_author['first_name']
            if en_author.get('middle_name'):
                initials_text += " " + en_author['middle_name'][0] + "."
            initials_elem = etree.SubElement(en_individ_info, 'initials')
            initials_elem.text = initials_text
            
            # Organization name (affiliation in English, fallback to Russian if empty)
            en_affiliation = author_settings.get(en_author['author_id'], {}).get('affiliation', {})
            if isinstance(en_affiliation, dict):
                org_name = en_affiliation.get('en_US', '')
                if not org_name:
                    # Fallback to Russian affiliation if English is empty
                    org_name = en_affiliation.get('ru_RU', '')
            else:
                org_name = en_affiliation
            if org_name:
                org_elem = etree.SubElement(en_individ_info, 'orgName')
                org_elem.text = org_name
            
            # Email
            email_elem = etree.SubElement(en_individ_info, 'email')
            email_elem.text = en_author.get('email', '')
            
            # Biography in English
            en_bio = author_settings.get(en_author['author_id'], {}).get('biography', {})
            if isinstance(en_bio, dict):
                bio_text = en_bio.get('en_US', '')
            else:
                bio_text = en_bio
            if bio_text:
                bio_elem = etree.SubElement(en_individ_info, 'bio')
                bio_elem.text = clean_html(bio_text)
        
        # Add authorCodes with ORCID if available (preferably from Russian author)
        orcid_author = ru_author if ru_author else en_author
        if orcid_author:
            orcid_raw = author_settings.get(orcid_author['author_id'], {}).get('orcid', {})
            if isinstance(orcid_raw, dict):
                # locale is usually empty string for orcid
                orcid_value = orcid_raw.get('', '') or next(iter(orcid_raw.values()), '')
            else:
                orcid_value = orcid_raw or ''
            if orcid_value:
                orcid_clean = re.sub(r'^https?://orcid\.org/', '', str(orcid_value)).strip()
                if orcid_clean:
                    author_codes_elem = etree.SubElement(author_elem, 'authorCodes')
                    orcid_elem = etree.SubElement(author_codes_elem, 'orcid')
                    orcid_elem.text = orcid_clean
    
    # Add article titles
    art_titles_elem = etree.SubElement(article_elem, 'artTitles')
    
    # Russian title
    title_ru = get_setting(article_data.get('article_settings', []), 'title', 'ru_RU')
    if title_ru:
        art_title_ru = etree.SubElement(art_titles_elem, 'artTitle')
        art_title_ru.set('lang', 'ru')
        art_title_ru.text = title_ru
    
    # English title
    title_en = get_setting(article_data.get('article_settings', []), 'title', 'en_US')
    if title_en:
        art_title_en = etree.SubElement(art_titles_elem, 'artTitle')
        art_title_en.set('lang', 'en')
        art_title_en.text = title_en
    
    # Add abstracts
    abstracts_elem = etree.SubElement(article_elem, 'abstracts')
    
    # Russian abstract
    abstract_ru = get_setting(article_data.get('article_settings', []), 'abstract', 'ru_RU')
    if abstract_ru:
        abstract_ru_elem = etree.SubElement(abstracts_elem, 'abstract')
        abstract_ru_elem.set('lang', 'ru')
        abstract_ru_elem.text = clean_html(abstract_ru)
    
    # English abstract
    abstract_en = get_setting(article_data.get('article_settings', []), 'abstract', 'en_US')
    if abstract_en:
        abstract_en_elem = etree.SubElement(abstracts_elem, 'abstract')
        abstract_en_elem.set('lang', 'en')
        abstract_en_elem.text = clean_html(abstract_en)
    
    # Add keywords
    keywords_elem = etree.SubElement(article_elem, 'keywords')
    
    # Russian keywords
    subject_settings = article_data.get('article_settings', [])
    keywords_ru = parse_keywords(get_setting(subject_settings, 'subject', 'ru_RU'))
    if keywords_ru:
        kwd_group_ru = etree.SubElement(keywords_elem, 'kwdGroup')
        kwd_group_ru.set('lang', 'ru')
        for keyword in keywords_ru:
            keyword_elem = etree.SubElement(kwd_group_ru, 'keyword')
            keyword_elem.text = keyword
    
    # English keywords
    keywords_en = parse_keywords(get_setting(subject_settings, 'subject', 'en_US'))
    if keywords_en:
        kwd_group_en = etree.SubElement(keywords_elem, 'kwdGroup')
        kwd_group_en.set('lang', 'en')
        for keyword in keywords_en:
            keyword_elem = etree.SubElement(kwd_group_en, 'keyword')
            keyword_elem.text = keyword
    
    # Add dates (only if at least one date is present)
    dates_elem = etree.Element('dates')
    date_submitted = article.get('date_submitted')
    ds = _fmt_date(date_submitted)
    if ds:
        date_received_elem = etree.SubElement(dates_elem, 'dateReceived')
        date_received_elem.text = ds
    publication = article_data.get('publishedinfo') or article_data.get('publication') or {}
    date_published = publication.get('date_published')
    dp = _fmt_date(date_published)
    if dp:
        date_pub_elem = etree.SubElement(dates_elem, 'datePublication')
        date_pub_elem.text = dp
    if len(dates_elem):  # only append if has children
        article_elem.append(dates_elem)
    
    # Add references (citations) — only if non-empty
    references_elem = etree.Element('references')
    citations = article_data.get('citations', [])
    sorted_citations = sorted(citations, key=lambda x: x['seq'])
    for citation in sorted_citations:
        ref_elem = etree.SubElement(references_elem, 'reference')
        ref_elem.text = citation.get('raw_citation', '')
    if len(references_elem):  # only append if has children
        article_elem.append(references_elem)
    
    return article_elem


# Export the required functions
__all__ = ['build_article_element', 'clean_html', 'parse_pages']