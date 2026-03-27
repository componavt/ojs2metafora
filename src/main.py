# main.py
import os
import pymysql
from lxml import etree
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset=os.getenv("DB_CHARSET", "utf8mb4"),
        cursorclass=pymysql.cursors.DictCursor,
    )

def fetch_one_article(conn, article_id=1, locale="ru_RU"):
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM articles WHERE article_id=%s", (article_id,))
        article = cur.fetchone()
        if not article:
            raise RuntimeError("Article not found")

        cur.execute(
            """
            SELECT setting_value AS title
            FROM article_settings
            WHERE article_id=%s AND setting_name='title' AND locale=%s
            """,
            (article_id, locale),
        )
        title_row = cur.fetchone()
        title = title_row["title"] if title_row else "Без названия"

    return article, title

def build_minimal_journal_xml(article, title):
    NSMAP = None  # journal3.xsd без пространств имён, обычный XML
    root = etree.Element("journal", nsmap=NSMAP)

    issue = etree.SubElement(root, "issue")
    # Минимум для запуска: год + страницы выпуска/статьи
    iss_title = etree.SubElement(issue, "issTitle")
    iss_title.text = "Тестовый выпуск"

    articles_el = etree.SubElement(issue, "articles")
    article_el = etree.SubElement(articles_el, "article")

    # Язык публикации
    lang_publ = etree.SubElement(article_el, "langPubl")
    lang_publ.text = (article.get("language") or "ru")[:2]

    # Страницы
    pages_el = etree.SubElement(article_el, "pages")
    pages_el.text = article.get("pages") or ""

    # Заголовок статьи
    art_titles = etree.SubElement(article_el, "artTitles")
    art_title = etree.SubElement(art_titles, "artTitle")
    art_title.set("lang", "ru")
    art_title.text = title

    return etree.ElementTree(root)

def main():
    conn = get_connection()
    try:
        article, title = fetch_one_article(conn, article_id=1, locale="ru_RU")
    finally:
        conn.close()

    tree = build_minimal_journal_xml(article, title)
    os.makedirs("output", exist_ok=True)
    output_path = os.path.join("output", "output_journal.xml")
    tree.write(output_path, encoding="utf-8", xml_declaration=True, pretty_print=True)
    print(f"XML saved to {output_path}")

if __name__ == "__main__":
    main()
