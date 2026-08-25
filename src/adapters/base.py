"""
Abstract base class for OJS database adapters.

This module defines the adapter contract that all OJS version adapters must implement.
"""
import abc
from typing import Dict, List, Any


class OjsAdapter(metaclass=abc.ABCMeta):
    """
    Abstract base class defining the adapter contract for OJS metadata extraction.
    
    All adapter implementations must extend this class and implement the
    abstract methods for fetching article, issue, and section metadata.
    """
    
    def __init__(self, source_key: str):
        """
        Initialize the adapter with the source key.
        
        Args:
            source_key: The key identifying the source profile.
        """
        self.source_key = source_key
    
    @abc.abstractmethod
    def fetch_article_metadata(self, article_id: int) -> Dict[str, Any]:
        """
        Fetch complete metadata for a single article.
        
        Args:
            article_id: The ID of the article to fetch.
        
        Returns:
            Dictionary containing all article metadata with normalized structure:

            Top-level keys (normalized across all OJS versions):
            - article_id: OJS24 articles.article_id, OJS31 submissions.submission_id
            - article: article row with article_id, journal_id, etc.
            - published_info: OJS24 published_articles, OJS31 published_submissions row
              - published_article_id: alias to published_submissions.published_submission_id
            - issue: issue row (volume, number, year, date_published, etc.)
            - issue_settings: OJS24 issue_settings rows
            - journal: journal row (path, primary_locale, etc.)
            - journal_settings: journal_settings rows
            - section: section row (if applicable)
            - section_settings: section_settings rows
            - article_settings: OJS24 article_settings rows, OJS31 submission_settings plus
              synthetic subject rows derived from controlled vocabulary keywords
            - authors: authors rows ordered by seq
            - author_settings: author_settings rows
            - citations: citations rows ordered by seq

            Optional normalized field:
            - publication_date (OJS31 only): optional ISO date string (YYYY-MM-DD)
              containing the formal issue year to use for XML <datePublication>.
              When present, overrides published_info.date_published. This exists to
              preserve source-specific formal publication semantics without making
              xml_generator.py branch on source or OJS version. For MGTA/OJS31, this
              is set to YYYY-01-01 using the issue.year field. For OJS24, this field
              is not supplied and legacy behavior persists.

            Note: The actual OJS database timestamps in published_info.date_published
            and issue.date_published are preserved unchanged. The publication_date
            override is an additional normalized field that downstream XML generation
            can use to implement source-specific publication date policies.
        """
        pass
    
    @abc.abstractmethod
    def fetch_issue_article_ids(self, issue_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all published article IDs for a given issue.
        
        Args:
            issue_id: The ID of the issue.
        
        Returns:
            List of dictionaries with keys: article_id, seq, section_id.
        """
        pass
    
    @abc.abstractmethod
    def fetch_issue_metadata(self, issue_id: int) -> Dict[str, Any]:
        """
        Fetch issue and journal metadata for a given issue.
        
        Args:
            issue_id: The ID of the issue.
        
        Returns:
            Dictionary containing issue and journal metadata with keys:
            - issue_id, journal_id, volume, number, year, date_published
            - print_issn, online_issn, title_ru, title_en, publisher, journal_path
        """
        pass
    
    @abc.abstractmethod
    def get_section_titles(self, section_id: int) -> Dict[str, str]:
        """
        Fetch titles for a given section.
        
        Args:
            section_id: The ID of the section.
        
        Returns:
            Dictionary with keys: title_ru, title_en.
        """
        pass
