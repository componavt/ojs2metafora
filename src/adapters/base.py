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
            Dictionary containing all article metadata with keys:
            - article_id
            - article
            - published_info
            - issue
            - issue_settings
            - journal
            - journal_settings
            - section
            - section_settings
            - article_settings
            - authors
            - author_settings
            - citations
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
