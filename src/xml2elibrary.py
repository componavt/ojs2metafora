"""
Convert a Metafora issue XML into RCSI elibrary-compatible XML.

Reads an already-generated issue XML (e.g. output/2025/precambrian_n5.xml),
scans a prepared issue directory for article PDFs, matches them to articles,
converts language codes, adds <files> elements, and writes the result.

Usage:
    python src/xml2elibrary.py output/2025/precambrian_n5.xml \
        output/journals.rcsi.science/2025/1997-3217_2025_5 \
        --output output/journals.rcsi.science/2025/1997-3217_2025_5/1997-3217_2025_5.xml \
        --validate --verbose
"""

import argparse
import logging
import os
import re
import sys
from pathlib import Path

from lxml import etree

logger = logging.getLogger(__name__)

# Language code conversion: 2-letter ISO -> 3-letter RCSI style
LANG_MAP = {
    'ru': 'RUS',
    'en': 'ENG',
}

# Canonical section order for this journal (lowercase keywords)
SECTION_ORDER = [
    'editorial',
    'reviews',
    'review articles',
    'short communications',
    'short reports',
    'history of science',
    'chronicle',
    'dates and anniversaries',
    'юбилеи',
    'даты',
    'хроника',
    'история науки',
    'обзор',
    'кратк',
    'от редактор',
    'предисловие',
]


def convert_lang(code: str) -> str:
    """Convert a 2-letter language code to 3-letter RCSI style."""
    if not code:
        return code
    return LANG_MAP.get(code.lower().strip(), code.upper())


def scan_article_pdfs(issue_dir: Path) -> list[tuple[int, str, Path]]:
    """
    Scan the issue directory and collect article PDFs with numeric prefix.

    Returns list of (numeric_prefix, filename, filepath) sorted by prefix.
    Excludes 'PDF all.pdf' and non-PDF files.
    """
    pdfs = []
    for entry in issue_dir.iterdir():
        if not entry.is_file() or not entry.name.endswith('.pdf'):
            continue
        if entry.name.lower() == 'pdf all.pdf':
            logger.debug("Skipping combined PDF: %s", entry.name)
            continue
        m = re.match(r'^(\d+)\s+(.+)$', entry.name)
        if m:
            prefix = int(m.group(1))
            pdfs.append((prefix, entry.name, entry))
            logger.debug("Found article PDF: %s (prefix=%d)", entry.name, prefix)
        else:
            logger.debug("Skipping non-article PDF: %s", entry.name)
    pdfs.sort(key=lambda x: x[0])
    return pdfs


def parse_page_range(pages_text: str) -> tuple[int, int] | None:
    """
    Parse a page range string like '5-10' or '44' into (start, end).
    Returns None if parsing fails.
    """
    if not pages_text:
        return None
    text = pages_text.strip().replace('\u2013', '-').replace('\u2014', '-')
    parts = text.split('-')
    try:
        if len(parts) >= 2:
            return int(parts[0].strip()), int(parts[1].strip())
        elif len(parts) == 1:
            p = int(parts[0].strip())
            return p, p
    except ValueError:
        pass
    return None


def extract_articles_from_xml(tree: etree._ElementTree) -> list[dict]:
    """
    Extract article info from the source XML tree.

    Returns list of dicts with keys:
        element: the <article> lxml element
        section: the parent <section> element or None
        pages_text: raw pages string
        page_start: first page number (or None)
        page_end: last page number (or None)
        title_ru: Russian title text (or empty)
        doi: DOI text (or empty)
    """
    articles = []
    root = tree.getroot()
    issue_elem = root.find('issue')
    if issue_elem is None:
        logger.error("No <issue> element found in source XML")
        return articles

    articles_container = issue_elem.find('articles')
    if articles_container is None:
        logger.error("No <articles> container found in source XML")
        return articles

    current_section = None
    for child in articles_container:
        if child.tag == 'section':
            current_section = child
            continue
        if child.tag != 'article':
            continue

        pages_elem = child.find('pages')
        pages_text = pages_elem.text if pages_elem is not None else ''
        page_range = parse_page_range(pages_text)

        title_ru = ''
        art_titles = child.find('artTitles')
        if art_titles is not None:
            for t in art_titles.findall('artTitle'):
                if t.get('lang', '').lower() in ('ru', 'rus', 'ru_ru'):
                    title_ru = (t.text or '').strip()
                    break

        doi = ''
        codes_elem = child.find('codes')
        if codes_elem is not None:
            doi_elem = codes_elem.find('doi')
            if doi_elem is not None:
                doi = (doi_elem.text or '').strip()

        articles.append({
            'element': child,
            'section': current_section,
            'pages_text': pages_text,
            'page_start': page_range[0] if page_range else None,
            'page_end': page_range[1] if page_range else None,
            'title_ru': title_ru,
            'doi': doi,
        })

    return articles


def determine_article_order(
    xml_articles: list[dict],
    pdf_list: list[tuple[int, str, Path]],
) -> list[dict]:
    """
    Determine the correct article order.

    Strategy:
    1. Compare XML order to PDF order by checking if page numbers align with PDF prefixes.
    2. If inconsistent (which is typical: XML is in section order, PDFs in page order),
       reorder articles by page number.
    3. Articles without pages go to the end.
    """
    n_articles = len(xml_articles)
    n_pdfs = len(pdf_list)

    logger.info("XML has %d articles, directory has %d article PDFs", n_articles, n_pdfs)

    if n_articles == 0:
        return xml_articles

    # Check if XML order matches PDF order by comparing first page to PDF prefix
    orders_consistent = True
    if n_articles == n_pdfs and n_articles > 0:
        for i in range(n_articles):
            pdf_prefix = pdf_list[i][0]
            art = xml_articles[i]
            if art['page_start'] is not None:
                # PDF prefix should roughly match article position in page order
                # If the first XML article has page_start != 0 (or != first PDF prefix),
                # the order is likely different
                if i == 0 and art['page_start'] != pdf_prefix:
                    orders_consistent = False
                    break
            else:
                # Article without pages at a non-end position is suspicious
                if i < n_articles - 1:
                    orders_consistent = False
                    break
    else:
        orders_consistent = False

    if not orders_consistent:
        logger.info("XML order does NOT match PDF order; reordering by page number")

        # Log the discrepancy
        for i in range(min(n_articles, n_pdfs)):
            pdf_prefix = pdf_list[i][0]
            pdf_name = pdf_list[i][1]
            art = xml_articles[i]
            logger.debug(
                "Position %d: PDF='%s' (prefix=%d) vs article='%s' (pages=%s)",
                i, pdf_name, pdf_prefix, art['title_ru'][:60], art['pages_text']
            )

        # Reorder by page number
        articles_with_pages = [a for a in xml_articles if a['page_start'] is not None]
        articles_without_pages = [a for a in xml_articles if a['page_start'] is None]

        articles_with_pages.sort(key=lambda a: a['page_start'])

        if articles_without_pages:
            logger.warning(
                "%d article(s) without page ranges will be placed at the end",
                len(articles_without_pages),
            )

        result = articles_with_pages + articles_without_pages

        # Log the new order
        logger.info("New article order (by page number):")
        for i, art in enumerate(result):
            logger.debug(
                "  %d: '%s' (pages=%s)",
                i, art['title_ru'][:60], art['pages_text']
            )

        return result

    logger.info("Article order in XML already matches PDF order by position")
    return xml_articles


def transform_lang_attributes(root: etree._Element):
    """
    Walk the XML tree and convert lang attributes and langPubl text
    from 2-letter to 3-letter RCSI style.
    """
    converted_count = 0

    for elem in root.iter():
        lang_attr = elem.get('lang')
        if lang_attr:
            new_lang = convert_lang(lang_attr)
            if new_lang != lang_attr:
                elem.set('lang', new_lang)
                converted_count += 1

        if elem.tag == 'langPubl' and elem.text:
            new_lang = convert_lang(elem.text)
            if new_lang != elem.text:
                elem.text = new_lang
                converted_count += 1

    logger.info("Converted %d lang attributes/texts to RCSI style", converted_count)


def match_pdfs_to_articles(
    articles: list[dict],
    pdf_list: list[tuple[int, str, Path]],
) -> dict:
    """
    Match PDF files to articles by sorted position.

    Returns dict mapping article element -> pdf filename.
    """
    mapping = {}
    n_articles = len(articles)
    n_pdfs = len(pdf_list)

    match_count = min(n_articles, n_pdfs)
    for i in range(match_count):
        art = articles[i]
        pdf_prefix, pdf_name, pdf_path = pdf_list[i]
        mapping[art['element']] = pdf_name
        logger.debug(
            "Matched article '%s' (pages=%s) -> '%s'",
            art['title_ru'][:60], art['pages_text'], pdf_name,
        )

    if n_pdfs > n_articles:
        for i in range(n_articles, n_pdfs):
            logger.warning(
                "Extra PDF without matching article: %s (prefix=%d)",
                pdf_list[i][1], pdf_list[i][0],
            )

    if n_articles > n_pdfs:
        for i in range(n_pdfs, n_articles):
            logger.warning(
                "Article without matching PDF: '%s' (pages=%s)",
                articles[i]['title_ru'][:60], articles[i]['pages_text'],
            )

    return mapping


def add_files_to_articles(articles_container: etree._Element, pdf_mapping: dict):
    """
    Add <files> elements to each <article> in the container.
    The lang attribute is derived from the article's <langPubl> element.
    """
    for child in articles_container:
        if child.tag != 'article':
            continue
        pdf_name = pdf_mapping.get(child)
        if pdf_name:
            files_elem = etree.SubElement(child, 'files')
            file_elem = etree.SubElement(files_elem, 'file')
            file_elem.set('desc', 'fullText')
            file_elem.text = pdf_name
            lang_publ = child.find('langPubl')
            if lang_publ is not None and lang_publ.text:
                file_elem.set('lang', convert_lang(lang_publ.text))
            logger.debug("Added <files> to article: %s", pdf_name)


def rebuild_articles_container(
    articles_container: etree._Element,
    ordered_articles: list[dict],
):
    """
    Rebuild the <articles> container so that sections and articles
    appear in the page-number order determined by PDF matching.

    Preserves section headers and groups articles under their original sections.
    """
    if articles_container is None:
        return

    # Clear all children
    for child in list(articles_container):
        articles_container.remove(child)

    # Group articles by section in the new order
    seen_sections = set()
    current_section_elem = None

    for art in ordered_articles:
        section_elem = art['section']

        if section_elem is not None and id(section_elem) not in seen_sections:
            # Deep-copy the section element (without its original articles)
            new_section = etree.SubElement(articles_container, 'section')
            for sec_child in section_elem:
                new_section.append(deepcopy_element(sec_child))
            current_section_elem = new_section
            seen_sections.add(id(section_elem))
        elif section_elem is None and current_section_elem is None:
            # Article without a section — shouldn't normally happen, but handle it
            pass

        # Append the article element (already modified with lang conversions)
        articles_container.append(art['element'])

    logger.info("Rebuilt <articles> container with %d sections in page order", len(seen_sections))


def deepcopy_element(elem: etree._Element) -> etree._Element:
    """Create a deep copy of an lxml element."""
    new_elem = etree.Element(elem.tag)
    for key, val in elem.attrib.items():
        new_elem.set(key, val)
    if elem.text:
        new_elem.text = elem.text
    if elem.tail:
        new_elem.tail = elem.tail
    for child in elem:
        new_elem.append(deepcopy_element(child))
    return new_elem


def validate_xml_against_xsd(xml_path: str, xsd_path: str) -> bool:
    """Validate XML file against XSD schema."""
    try:
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f)
        schema = etree.XMLSchema(schema_doc)

        with open(xml_path, 'rb') as f:
            xml_doc = etree.parse(f)

        is_valid = schema.validate(xml_doc)
        if not is_valid:
            logger.error("XSD validation FAILED:")
            for error in schema.error_log:
                logger.error("  Line %d: %s", error.line, error.message)
            return False
        logger.info("XSD validation PASSED")
        return True
    except Exception as e:
        logger.error("XSD validation error: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Convert Metafora issue XML to RCSI elibrary-compatible XML'
    )
    parser.add_argument(
        'source_xml',
        help='Path to the source Metafora XML file'
    )
    parser.add_argument(
        'issue_dir',
        help='Path to the prepared issue directory (contains PDFs)'
    )
    parser.add_argument(
        '--output', '-o',
        help='Output XML file path (default: <issue_dir>/<issn>_<year>_<number>.xml)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate output XML against XSD schema'
    )
    parser.add_argument(
        '--xsd-path',
        default=str(Path(__file__).parent.parent / 'schemas' / 'journal3.xsd'),
        help='Path to journal3.xsd (default: schemas/journal3.xsd)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable DEBUG logging'
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    source_xml = Path(args.source_xml)
    issue_dir = Path(args.issue_dir)

    if not source_xml.is_file():
        logger.error("Source XML not found: %s", source_xml)
        sys.exit(1)
    if not issue_dir.is_dir():
        logger.error("Issue directory not found: %s", issue_dir)
        sys.exit(1)

    logger.info("Reading source XML: %s", source_xml)
    tree = etree.parse(str(source_xml))

    logger.info("Scanning issue directory: %s", issue_dir)
    pdf_list = scan_article_pdfs(issue_dir)
    if not pdf_list:
        logger.warning("No article PDFs found in %s", issue_dir)

    logger.info("Extracting articles from XML")
    xml_articles = extract_articles_from_xml(tree)
    if not xml_articles:
        logger.error("No articles found in source XML")
        sys.exit(1)

    logger.info("Determining article order")
    ordered_articles = determine_article_order(xml_articles, pdf_list)

    logger.info("Converting language codes to RCSI style")
    transform_lang_attributes(tree.getroot())

    logger.info("Matching PDFs to articles")
    pdf_mapping = match_pdfs_to_articles(ordered_articles, pdf_list)

    root = tree.getroot()
    issue_elem = root.find('issue')
    articles_container = issue_elem.find('articles') if issue_elem is not None else None

    if articles_container is not None:
        logger.info("Rebuilding <articles> container in page order")
        rebuild_articles_container(articles_container, ordered_articles)

        logger.info("Matching PDFs to articles")
        pdf_mapping = match_pdfs_to_articles(ordered_articles, pdf_list)

        logger.info("Adding <files> elements to articles")
        add_files_to_articles(articles_container, pdf_mapping)
    else:
        logger.warning("No <articles> container found; skipping <files> addition")
        pdf_mapping = {}

    output_path = args.output
    if not output_path:
        issn_elem = root.find('issn')
        issn = (issn_elem.text or '').strip() if issn_elem is not None else ''
        issue_elem = root.find('issue')
        year = ''
        number = ''
        if issue_elem is not None:
            year_elem = issue_elem.find('dateUni')
            number_elem = issue_elem.find('number')
            year = (year_elem.text or '').strip() if year_elem is not None else ''
            number = (number_elem.text or '').strip() if number_elem is not None else ''
        filename = f"{issn}_{year}_{number}.xml" if issn and year and number else "elibrary.xml"
        output_path = str(issue_dir / filename)

    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    tree.write(
        output_path,
        encoding='utf-8',
        xml_declaration=True,
        pretty_print=True
    )
    logger.info("Output XML written: %s", output_path)

    if args.validate:
        xsd_path = args.xsd_path
        if not Path(xsd_path).exists():
            xsd_path = 'schemas/journal3.xsd'
        if Path(xsd_path).exists():
            validate_xml_against_xsd(output_path, xsd_path)
        else:
            logger.warning("XSD schema not found at %s; skipping validation", xsd_path)


if __name__ == '__main__':
    main()
