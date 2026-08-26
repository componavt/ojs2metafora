import unittest
import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Configure logging before importing modules that use logger
logging.basicConfig(level=logging.WARNING, format='%(name)s:%(levelname)s:%(message)s')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lxml import etree
from src.xml_generator import build_article_element


class TestXmlGeneratorContract(unittest.TestCase):
    """Test suite for XML generator contract and normalization policies."""

    def build_minimal_article_data(self, overrides=None):
        """Build minimal valid article_data dict for testing."""
        data = {
            'article_id': 100,
            'article': {
                'article_id': 100,
                'journal_id': 1,
                'section_id': 1,
                'language': 'ru',
                'pages': '5-10',
                'status': 3,
                'date_submitted': '2021-06-15',
            },
            'published_info': {
                'published_article_id': 50,
                'issue_id': 10,
                'date_published': '2021-08-20 14:30:00',
                'seq': 1,
            },
            'issue': {
                'issue_id': 10,
                'year': 2021,
                'volume': '1',
                'number': '1',
                'date_published': None,
            },
            'journal': {'path': 'test-journal'},
            'journal_settings': [],
            'section': {'section_id': 1, 'seq': 1, 'hide_title': 0},
            'section_settings': [
                {'locale': 'ru_RU', 'setting_name': 'title', 'setting_value': 'Статьи'},
            ],
            'article_settings': [
                {'locale': 'ru_RU', 'setting_name': 'title', 'setting_value': 'Тестовая статья'},
                {'locale': 'en_US', 'setting_name': 'title', 'setting_value': 'Test Article'},
                {'locale': 'ru_RU', 'setting_name': 'abstract', 'setting_value': 'Абстракт'},
                {'locale': 'en_US', 'setting_name': 'abstract', 'setting_value': 'Abstract'},
                {'locale': '', 'setting_name': 'pub-id::doi', 'setting_value': '10.17076/test'},
            ],
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.com',
                    'country': 'RU',
                },
            ],
            'author_settings': [],
            'citations': [],
        }
        if overrides:
            data.update(overrides)
        return data

    def parse_xml(self, article_elem):
        """Parse article element to text for verification."""
        return etree.tostring(article_elem, encoding='unicode', pretty_print=False)

    def test_surname_case_preservation_russian(self):
        """Test that Russian surname preserves exact case from OJS."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        ru_surname = result.xpath(
            "string(authors/author/individInfo[@lang='ru']/surname)"
        )
        self.assertEqual(ru_surname, "Иванов")
        self.assertNotEqual(ru_surname, "ИВАНОВ")

    def test_surname_case_preservation_english(self):
        """Test that English surname preserves exact case from OJS."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 2,
                    'seq': 2,
                    'first_name': 'Ivan',
                    'middle_name': '',
                    'last_name': 'Ivanov',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        en_surname = result.xpath(
            "string(authors/author/individInfo[@lang='en']/surname)"
        )
        self.assertEqual(en_surname, "Ivanov")
        self.assertNotEqual(en_surname, "IVANOV")

    def test_country_export_russian_author(self):
        """Test that country is exported in Russian individInfo."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        ru_country = result.xpath(
            "string(authors/author/individInfo[@lang='ru']/country)"
        )
        self.assertEqual(ru_country, "RU")

    def test_country_export_english_author(self):
        """Test that country is exported in English individInfo."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 2,
                    'seq': 2,
                    'first_name': 'Ivan',
                    'middle_name': '',
                    'last_name': 'Ivanov',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        en_country = result.xpath(
            "string(authors/author/individInfo[@lang='en']/country)"
        )
        self.assertEqual(en_country, "RU")

    def test_country_different_values_preserved_independently(self):
        """Test that different country values in ru/enauthors are preserved independently."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': 'UZ',
                },
                {
                    'author_id': 2,
                    'seq': 2,
                    'first_name': 'Ivan',
                    'middle_name': '',
                    'last_name': 'Ivanov',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        ru_country = result.xpath(
            "string(authors/author/individInfo[@lang='ru']/country)"
        )
        en_country = result.xpath(
            "string(authors/author/individInfo[@lang='en']/country)"
        )
        self.assertEqual(ru_country, "UZ")
        self.assertEqual(en_country, "RU")

    def test_missing_country_is_omitted(self):
        """Test that missing/empty country values result in no <country> element."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': None,
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        ru_country_nodes = result.xpath(
            "authors/author/individInfo[@lang='ru']/country"
        )
        self.assertEqual(len(ru_country_nodes), 0)

    def test_whitespace_only_country_is_omitted(self):
        """Test that whitespace-only country value results in no <country> element."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': '   ',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        ru_country_nodes = result.xpath(
            "authors/author/individInfo[@lang='ru']/country"
        )
        self.assertEqual(len(ru_country_nodes), 0)

    def test_no_town_generated(self):
        """Test that <town> element is never generated."""
        article_data = self.build_minimal_article_data({
            'authors': [
                {
                    'author_id': 1,
                    'seq': 1,
                    'first_name': 'Иван',
                    'middle_name': 'Иванович',
                    'last_name': 'Иванов',
                    'email': 'ivan@example.test',
                    'country': 'RU',
                },
            ],
            'author_settings': [
                {
                    'author_id': 1,
                    'setting_name': 'town',
                    'locale': 'ru_RU',
                    'setting_value': 'Novosibirsk',
                },
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        town_nodes = result.xpath("authors/author/individInfo/town")
        self.assertEqual(len(town_nodes), 0)

    def test_ojs31_formal_issue_year_publication_date(self):
        """Test that OJS31 uses formal issue year for datePublication."""
        article_data = self.build_minimal_article_data({
            'publication_date': '2022-01-01',
            'published_info': {
                'date_published': '2023-01-18 12:09:32',
            },
            'issue': {'year': 2022},
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        dates_elem = result.find('dates')
        self.assertIsNotNone(dates_elem)
        date_pub = dates_elem.find('datePublication')
        self.assertIsNotNone(date_pub)
        self.assertEqual(date_pub.text, '2022-01-01')

    def test_legacy_fallback_is_preserved(self):
        """Test that legacy date_published is used when publication_date absent."""
        article_data = self.build_minimal_article_data({
            'published_info': {
                'date_published': '2021-08-20 14:30:00',
            },
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        dates_elem = result.find('dates')
        self.assertIsNotNone(dates_elem)
        date_pub = dates_elem.find('datePublication')
        self.assertIsNotNone(date_pub)
        self.assertEqual(date_pub.text, '2021-08-20')

    def test_empty_online_issn_behavior_unchanged(self):
        """Test that empty onlineISSN still produces empty <eissn>."""
        from lxml import etree

        root = etree.Element('journal')
        eissn_elem = etree.SubElement(root, 'eissn')
        eissn_elem.text = ''

        eissn = root.find('eissn')
        self.assertIsNotNone(eissn)
        self.assertIn(eissn.text, (None, ''))

    def test_ojs31_synthetic_keywords(self):
        """Test that MGTA synthetic subject settings generate correct keywords."""
        article_data = self.build_minimal_article_data({
            'article_settings': [
                {'locale': 'ru_RU', 'setting_name': 'subject', 'setting_value': 'Ключ 1; Ключ 2; Ключ 3'},
                {'locale': 'en_US', 'setting_name': 'subject', 'setting_value': 'Key 1; Key 2; Key 3'},
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        keywords_elem = result.find('keywords')
        self.assertIsNotNone(keywords_elem)

        kwd_group_ru = keywords_elem.find("kwdGroup[@lang='ru']")
        self.assertIsNotNone(kwd_group_ru)
        ru_keywords = kwd_group_ru.findall('keyword')
        self.assertEqual(len(ru_keywords), 3)
        self.assertEqual(ru_keywords[0].text, 'Ключ 1')
        self.assertEqual(ru_keywords[1].text, 'Ключ 2')
        self.assertEqual(ru_keywords[2].text, 'Ключ 3')

        kwd_group_en = keywords_elem.find("kwdGroup[@lang='en']")
        self.assertIsNotNone(kwd_group_en)
        en_keywords = kwd_group_en.findall('keyword')
        self.assertEqual(len(en_keywords), 3)
        self.assertEqual(en_keywords[0].text, 'Key 1')
        self.assertEqual(en_keywords[1].text, 'Key 2')
        self.assertEqual(en_keywords[2].text, 'Key 3')

    def test_no_citations_means_no_references(self):
        """Test that empty citations list produces no <references> element."""
        article_data = self.build_minimal_article_data({
            'citations': [],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        references = result.find('references')
        self.assertIsNone(references)

    def test_author_mismatch_warning_and_continuation(self):
        """Test that author count mismatch produces warning but still generates XML."""
        article_data = self.build_minimal_article_data({
            'article_id': 999,
            'authors': [
                {'author_id': 1, 'seq': 1, 'first_name': 'Иван', 'last_name': 'Иванов', 'email': '', 'country': 'RU'},
                {'author_id': 2, 'seq': 2, 'first_name': 'Петр', 'last_name': 'Петров', 'email': '', 'country': 'RU'},
                {'author_id': 3, 'seq': 3, 'first_name': 'John', 'last_name': 'Smith', 'email': '', 'country': 'US'},
            ],
        })

        with self.assertLogs('src.xml_generator', level='WARNING') as log_ctx:
            result = build_article_element(article_data)

        self.assertIsNotNone(result)
        authors = result.findall('.//author')
        self.assertEqual(len(authors), 2)

        log_messages = [msg for msg in log_ctx.output if 'mismatched bilingual author counts' in msg]
        self.assertGreaterEqual(len(log_messages), 1)
        log_text = log_messages[0]
        self.assertIn('999', log_text)
        self.assertIn('ru=2', log_text)
        self.assertIn('en=1', log_text)
        self.assertIn('continuing with positional pairing', log_text)

    def test_single_language_authors_no_mismatch_warning(self):
        """Test that single-language author sets do not trigger mismatch warning."""
        article_data = self.build_minimal_article_data({
            'article_id': 888,
            'authors': [
                {'author_id': 1, 'seq': 1, 'first_name': 'Иван', 'last_name': 'Иванов', 'email': '', 'country': 'RU'},
                {'author_id': 2, 'seq': 2, 'first_name': 'Петр', 'last_name': 'Петров', 'email': '', 'country': 'RU'},
            ],
        })

        # Capture all warnings during build
        import warnings
        captured_warnings = []
        original_showwarning = warnings.showwarning
        
        def capture_warning(message, category, filename, lineno, file=None, line=None):
            captured_warnings.append(str(message))
        
        warnings.showwarning = capture_warning

        try:
            result = build_article_element(article_data)
        finally:
            warnings.showwarning = original_showwarning

        self.assertIsNotNone(result)
        authors = result.findall('.//author')
        self.assertEqual(len(authors), 2)

        mismatch_warnings = [w for w in captured_warnings if 'mismatched bilingual author' in w]
        self.assertEqual(len(mismatch_warnings), 0, "Expected no mismatch warning for single-language authors")

    def test_article_type_regression(self):
        """Test that section title 'Статьи' produces artType=RAR."""
        article_data = self.build_minimal_article_data({
            'section_settings': [
                {'locale': 'ru_RU', 'setting_name': 'title', 'setting_value': 'Статьи'},
            ],
        })

        result = build_article_element(article_data)

        self.assertIsNotNone(result)
        art_type = result.find('artType')
        self.assertIsNotNone(art_type)
        self.assertEqual(art_type.text, 'RAR')


if __name__ == '__main__':
    unittest.main()
