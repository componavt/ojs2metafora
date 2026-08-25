"""
OJS 3.1 metadata adapter (used by the "mgta" source profile).

Fetches article, issue, journal, section, and author metadata from an
OJS 3.1 database (submissions/submission_settings/published_submissions
schema), returning the same dictionary shapes as Ojs24Adapter so that
downstream XML generation code does not need to know which OJS version
produced the data.
"""

from src.adapters.base import OjsAdapter
from src.db_connector import get_connection


class Ojs31Adapter(OjsAdapter):

    def fetch_issue_article_ids(self, issue_id: int):
        connection = get_connection(self.source_key)
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT
                    ps.submission_id AS article_id,
                    ps.seq,
                    s.section_id
                FROM published_submissions AS ps
                JOIN submissions AS s
                  ON s.submission_id = ps.submission_id
                WHERE ps.issue_id = %s
                  AND s.status = 3
                ORDER BY ps.seq ASC
            """, (issue_id,))
            rows = cursor.fetchall()

            result = []
            for row in rows:
                result.append({
                    "article_id": row["article_id"],
                    "seq": row["seq"],
                    "section_id": row["section_id"],
                })

            return result
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def fetch_issue_metadata(self, issue_id: int):
        connection = get_connection(self.source_key)
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT i.issue_id, i.journal_id, i.volume, i.number,
                       i.year, i.date_published
                FROM issues i
                WHERE i.issue_id = %s
            """, (issue_id,))
            issue_row = cursor.fetchone()

            if not issue_row:
                raise ValueError(f"Issue with ID {issue_id} not found")

            issue_data = {
                "issue_id": issue_row["issue_id"],
                "journal_id": issue_row["journal_id"],
                "volume": issue_row["volume"],
                "number": issue_row["number"],
                "year": issue_row["year"],
                "date_published": issue_row["date_published"],
            }

            cursor.execute("""
                SELECT path FROM journals WHERE journal_id = %s
            """, (issue_data["journal_id"],))
            journal_path_row = cursor.fetchone()
            issue_data["journal_path"] = journal_path_row["path"] if journal_path_row else ""

            cursor.execute("""
                SELECT setting_name, locale, setting_value
                FROM journal_settings
                WHERE journal_id = %s
                  AND setting_name IN ('printIssn', 'onlineIssn', 'name', 'publisherInstitution')
            """, (issue_data["journal_id"],))
            journal_settings_rows = cursor.fetchall()

            journal_settings = {}
            for row in journal_settings_rows:
                setting_name = row["setting_name"]
                locale = row["locale"]
                setting_value = row["setting_value"]
                if setting_name not in journal_settings:
                    journal_settings[setting_name] = {}
                journal_settings[setting_name][locale] = setting_value

            issue_data["print_issn"] = journal_settings.get("printIssn", {}).get("", "")
            issue_data["online_issn"] = journal_settings.get("onlineIssn", {}).get("", "")
            issue_data["title_ru"] = journal_settings.get("name", {}).get("ru_RU", "")
            issue_data["title_en"] = journal_settings.get("name", {}).get("en_US", "")
            issue_data["publisher"] = journal_settings.get("publisherInstitution", {}).get("")

            return issue_data
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def get_section_titles(self, section_id: int):
        connection = get_connection(self.source_key)
        cursor = None
        try:
            cursor = connection.cursor()
            cursor.execute("""
                SELECT setting_name, locale, setting_value
                FROM section_settings
                WHERE section_id = %s
                  AND setting_name IN ('title', 'abbrev')
            """, (section_id,))
            rows = cursor.fetchall()

            titles = {}
            for row in rows:
                setting_name = row["setting_name"]
                locale = row["locale"]
                setting_value = row["setting_value"]
                if setting_name not in titles:
                    titles[setting_name] = {}
                titles[setting_name][locale] = setting_value

            title_ru = titles.get("title", {}).get("ru_RU", "")
            title_en = titles.get("title", {}).get("en_US", "")

            return {"title_ru": title_ru, "title_en": title_en}
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def fetch_article_metadata(self, article_id: int):
        connection = get_connection(self.source_key)
        cursor = None
        try:
            cursor = connection.cursor()

            cursor.execute("""
                SELECT
                    s.submission_id AS article_id,
                    s.locale,
                    s.context_id AS journal_id,
                    s.context_id,
                    s.section_id,
                    s.language,
                    s.pages,
                    s.date_submitted,
                    s.last_modified,
                    s.status,
                    s.citations AS raw_citations_field
                FROM submissions AS s
                WHERE s.submission_id = %(article_id)s
            """, {"article_id": article_id})
            submission_result = cursor.fetchone()

            if not submission_result:
                return None

            cursor.execute("""
                SELECT
                    ps.published_submission_id AS published_article_id,
                    ps.issue_id,
                    ps.date_published,
                    ps.seq
                FROM published_submissions AS ps
                WHERE ps.submission_id = %(article_id)s
            """, {"article_id": article_id})
            published_result = cursor.fetchone()

            issue_result = None
            issue_id = None
            if published_result:
                issue_id = published_result["issue_id"]
                cursor.execute("""
                    SELECT i.issue_id, i.journal_id, i.volume, i.number,
                           i.year, i.published, i.date_published AS issue_date_published
                    FROM issues i
                    WHERE i.issue_id = %(issue_id)s
                """, {"issue_id": issue_id})
                issue_result = cursor.fetchone()

            issue_settings = []
            if issue_id:
                cursor.execute("""
                    SELECT locale, setting_name, setting_value
                    FROM issue_settings
                    WHERE issue_id = %(issue_id)s
                    ORDER BY setting_name, locale
                """, {"issue_id": issue_id})
                issue_settings = cursor.fetchall()

            journal_id = submission_result["context_id"]
            section_id = submission_result["section_id"]

            cursor.execute("""
                SELECT j.journal_id, j.path, j.primary_locale, j.enabled
                FROM journals j
                WHERE j.journal_id = %(journal_id)s
            """, {"journal_id": journal_id})
            journal_result = cursor.fetchone()

            cursor.execute("""
                SELECT locale, setting_name, setting_value
                FROM journal_settings
                WHERE journal_id = %(journal_id)s
                  AND setting_name IN ('name', 'printIssn', 'onlineIssn', 'publisherInstitution')
                ORDER BY setting_name, locale
            """, {"journal_id": journal_id})
            journal_settings = cursor.fetchall()

            section_result = None
            section_settings = []
            if section_id:
                cursor.execute("""
                    SELECT s.section_id, s.journal_id, s.seq, s.hide_title
                    FROM sections s
                    WHERE s.section_id = %(section_id)s
                """, {"section_id": section_id})
                section_result = cursor.fetchone()

                if section_result:
                    cursor.execute("""
                        SELECT locale, setting_name, setting_value
                        FROM section_settings
                        WHERE section_id = %(section_id)s
                        ORDER BY setting_name, locale
                    """, {"section_id": section_id})
                    section_settings = cursor.fetchall()

            cursor.execute("""
                SELECT locale, setting_name, setting_value
                FROM submission_settings
                WHERE submission_id = %(article_id)s
                ORDER BY setting_name, locale
            """, {"article_id": article_id})
            submission_settings = cursor.fetchall()

            crossref_doi = None
            has_pubid_doi = False
            for row in submission_settings:
                if row["setting_name"] == "crossref::registeredDoi":
                    if row["setting_value"]:
                        crossref_doi = row["setting_value"]
                if row["setting_name"] == "pub-id::doi":
                    has_pubid_doi = True

            if not has_pubid_doi and crossref_doi:
                submission_settings.append({
                    "locale": "",
                    "setting_name": "pub-id::doi",
                    "setting_value": crossref_doi,
                })

            language = submission_result.get("language", "")
            if not language or not language.strip():
                language = "ru"
            submission_result["language"] = language

            cursor.execute("""
                SELECT cve.seq, cves.locale, cves.setting_value
                FROM controlled_vocabs AS cv
                JOIN controlled_vocab_entries AS cve
                  ON cve.controlled_vocab_id = cv.controlled_vocab_id
                JOIN controlled_vocab_entry_settings AS cves
                  ON cves.controlled_vocab_entry_id = cve.controlled_vocab_entry_id
                WHERE cv.symbolic = 'submissionKeyword'
                  AND cv.assoc_id = %(article_id)s
                  AND cves.setting_name = 'submissionKeyword'
                ORDER BY cve.seq ASC, cves.locale ASC
            """, {"article_id": article_id})
            keyword_rows = cursor.fetchall()

            keywords_by_locale = {}
            for row in keyword_rows:
                keywords_by_locale.setdefault(row["locale"], []).append(row["setting_value"])

            real_subject_by_locale = {}
            for row in submission_settings:
                if row["setting_name"] == "subject":
                    locale = row["locale"]
                    if row["setting_value"]:
                        real_subject_by_locale[locale] = row["setting_value"]

            for locale, words in keywords_by_locale.items():
                if locale in real_subject_by_locale:
                    continue
                normalized_value = "; ".join(words)
                submission_settings.append({
                    "locale": locale,
                    "setting_name": "subject",
                    "setting_value": normalized_value,
                })

            cursor.execute("""
                SELECT author_id, seq, primary_contact,
                       first_name, middle_name, last_name,
                       email, country, url
                FROM authors
                WHERE submission_id = %(article_id)s
                ORDER BY seq ASC
            """, {"article_id": article_id})
            authors = cursor.fetchall()

            author_settings = []
            if authors:
                author_ids = [a["author_id"] for a in authors]
                placeholders = ",".join(["%s"] * len(author_ids))
                cursor.execute(f"""
                    SELECT author_id, locale, setting_name, setting_value
                    FROM author_settings
                    WHERE author_id IN ({placeholders})
                    ORDER BY author_id, setting_name, locale
                """, author_ids)
                author_settings = cursor.fetchall()

            cursor.execute("""
                SELECT citation_id, seq, NULL AS citation_state, raw_citation
                FROM citations
                WHERE submission_id = %(article_id)s
                ORDER BY seq ASC
            """, {"article_id": article_id})
            citations = cursor.fetchall()

            return {
                "article_id": article_id,
                "article": submission_result,
                "published_info": published_result,
                "issue": issue_result,
                "issue_settings": issue_settings,
                "journal": journal_result,
                "journal_settings": journal_settings,
                "section": section_result,
                "section_settings": section_settings,
                "article_settings": submission_settings,
                "authors": authors,
                "author_settings": author_settings,
                "citations": citations,
            }
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()
