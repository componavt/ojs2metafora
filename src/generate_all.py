# Example usage:
# python generate_all.py --journal-path mathem
# python generate_all.py --journal-id 8 --output-dir output --validate --verbose
# python generate_all.py --journal-path mathem --dry-run
# python generate_all.py --journal-path mathem --year-from 2020 --year-to 2025

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db_connector import get_connection
from issue_builder import build_journal_xml, SERIES_MAP


logger = logging.getLogger(__name__)


def fetch_all_issues(journal_id=None, journal_path=None, year_from=None, year_to=None) -> list:
    """
    Fetch all published issues for a given journal.
    Either journal_id or journal_path must be provided.
    Returns a list of dicts with issue_id, number, year, date_published.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Resolve journal_id from journal_path if needed
        if journal_id is None and journal_path is not None:
            cursor.execute(
                "SELECT journal_id, path FROM journals WHERE path = %s",
                (journal_path,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Journal with path '{journal_path}' not found")
            journal_id = row['journal_id']

        # Fetch all published issues
        query = """
            SELECT i.issue_id, i.number, i.year, i.date_published
            FROM issues i
            WHERE i.journal_id = %s AND i.published = 1
            ORDER BY i.year ASC, i.number ASC
        """
        cursor.execute(query, (journal_id,))
        rows = cursor.fetchall()

        issues = []
        for row in rows:
            year = row['year']
            # Apply year filters
            if year_from is not None and (year is None or int(year) < year_from):
                continue
            if year_to is not None and (year is None or int(year) > year_to):
                continue
            issues.append({
                'issue_id': row['issue_id'],
                'number': row['number'],
                'year': row['year'],
                'date_published': row['date_published'],
            })

        return issues
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Generate Metaphora XML files for ALL published issues of a journal'
    )
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--journal-path', help='OJS journal path (e.g. "mathem", "biogeo")')
    group.add_argument('--journal-id', type=int, help='OJS journal_id integer')
    parser.add_argument('--output-dir', default=str(Path(__file__).parent.parent / 'output'), help='Base output directory (default: <project_root>/output)')
    parser.add_argument('--titleid', default='', help='Metaphora titleid string (default: empty)')
    parser.add_argument('--validate', action='store_true', help='Validate each XML against schemas/journal3.xsd')
    parser.add_argument('--year-from', type=int, help='Only process issues from this year onward')
    parser.add_argument('--year-to', type=int, help='Only process issues up to this year inclusive')
    parser.add_argument('--verbose', action='store_true', help='Enable DEBUG logging')
    parser.add_argument('--dry-run', action='store_true', help='Print issue list without generating files')
    parser.add_argument(
        '--all-journals',
        action='store_true',
        help='Process ALL journals defined in SERIES_MAP'
    )

    args = parser.parse_args()

    # Validate that at least one of --journal-path, --journal-id, or --all-journals is provided
    if not args.all_journals and args.journal_path is None and args.journal_id is None:
        parser.print_usage()
        print("error: one of --journal-path, --journal-id or --all-journals is required")
        sys.exit(1)

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if args.all_journals:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT journal_id, path FROM journals WHERE enabled = 1 ORDER BY path ASC"
            )
            journals = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        grand_total = 0
        grand_success = 0
        grand_failures = 0
        journal_count = len(journals)

        if args.dry_run:
            for row in journals:
                j_id = row['journal_id']
                j_path = row['path']
                issues = fetch_all_issues(journal_id=j_id, year_from=args.year_from, year_to=args.year_to)
                for issue in issues:
                    print(f"  {j_path}: issue_id={issue['issue_id']}  year={issue['year']}  n={issue['number']}")
            sys.exit(0)

        schemas_dir = Path(__file__).parent.parent / 'schemas'
        xsd_path = str(schemas_dir / 'journal3.xsd')
        if args.validate and not Path(xsd_path).exists():
            xsd_path = 'schemas/journal3.xsd'

        for row in journals:
            journal_id = row['journal_id']
            journal_path = row['path']
            try:
                issues = fetch_all_issues(journal_id=journal_id, year_from=args.year_from, year_to=args.year_to)
            except Exception as e:
                logging.error(f"Failed to fetch issues for {journal_path}: {e}", exc_info=True)
                print(f"Processing journal: {journal_path} (id={journal_id}) — 0 issues (error)")
                grand_failures += len(issues) if 'issues' in dir() else 0
                continue

            print(f"Processing journal: {journal_path} (id={journal_id}) — {len(issues)} issues")

            total = len(issues)
            success = 0
            failures = 0

            for issue_info in issues:
                issue_id = issue_info['issue_id']
                try:
                    logger.info(f"Processing issue_id={issue_id} year={issue_info['year']} n={issue_info['number']}...")

                    tree, meta = build_journal_xml(issue_id, titleid=args.titleid)

                    series_name = SERIES_MAP.get(meta.get('journal_path', ''), meta.get('journal_path', 'unknown'))
                    year = meta.get('year', 'unknown')
                    number = meta.get('number', '0')

                    year_dir = Path(args.output_dir) / year
                    year_dir.mkdir(parents=True, exist_ok=True)
                    output_path = year_dir / f'{series_name}_n{number}.xml'

                    tree.write(
                        str(output_path),
                        encoding='utf-8',
                        xml_declaration=True,
                        pretty_print=True
                    )

                    logger.info(f"Saved: {output_path}")

                    if args.validate:
                        from validator import validate_xml
                        is_valid = validate_xml(str(output_path), xsd_path)
                        if is_valid:
                            logger.info(f"Validation PASS: {output_path}")
                        else:
                            logger.warning(f"Validation FAIL: {output_path}")

                    success += 1

                except Exception as e:
                    logger.error(f"Error processing issue_id={issue_id}: {e}", exc_info=True)
                    failures += 1
                    continue

            grand_total += total
            grand_success += success
            grand_failures += failures

        print(f"Grand total: {journal_count} journals, {grand_success} issues processed, {grand_failures} failures")

        if grand_failures > 0:
            sys.exit(1)
        else:
            sys.exit(0)

    else:
        journal_id = args.journal_id
        journal_path = args.journal_path

        if journal_id is None:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT journal_id, path FROM journals WHERE path = %s",
                    (journal_path,)
                )
                row = cursor.fetchone()
                if not row:
                    logging.error(f"Journal with path '{journal_path}' not found in DB")
                    sys.exit(1)
                journal_id = row['journal_id']
            finally:
                cursor.close()
                conn.close()
        elif journal_path is None:
            conn = get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT journal_id, path FROM journals WHERE journal_id = %s",
                    (journal_id,)
                )
                row = cursor.fetchone()
                if not row:
                    logging.error(f"Journal with id {journal_id} not found in DB")
                    sys.exit(1)
                journal_path = row['path']
            finally:
                cursor.close()
                conn.close()

        try:
            issues = fetch_all_issues(
                journal_id=journal_id,
                journal_path=journal_path,
                year_from=args.year_from,
                year_to=args.year_to
            )
        except Exception as e:
            logging.error(f"Failed to fetch issues: {e}", exc_info=True)
            sys.exit(1)

        print(f"Found {len(issues)} issues for '{journal_path}' (id={journal_id})")

        if args.dry_run:
            for row in issues:
                print(f"  issue_id={row['issue_id']}  year={row['year']}  n={row['number']}")
            sys.exit(0)

        schemas_dir = Path(__file__).parent.parent / 'schemas'
        xsd_path = str(schemas_dir / 'journal3.xsd')
        if args.validate and not Path(xsd_path).exists():
            xsd_path = 'schemas/journal3.xsd'

        total = len(issues)
        success = 0
        failures = 0

        for issue_info in issues:
            issue_id = issue_info['issue_id']
            try:
                logger.info(f"Processing issue_id={issue_id} year={issue_info['year']} n={issue_info['number']}...")

                tree, meta = build_journal_xml(issue_id, titleid=args.titleid)

                series_name = SERIES_MAP.get(meta.get('journal_path', ''), meta.get('journal_path', 'unknown'))
                year = meta.get('year', 'unknown')
                number = meta.get('number', '0')

                year_dir = Path(args.output_dir) / year
                year_dir.mkdir(parents=True, exist_ok=True)
                output_path = year_dir / f'{series_name}_n{number}.xml'

                tree.write(
                    str(output_path),
                    encoding='utf-8',
                    xml_declaration=True,
                    pretty_print=True
                )

                logger.info(f"Saved: {output_path}")

                if args.validate:
                    from validator import validate_xml
                    is_valid = validate_xml(str(output_path), xsd_path)
                    if is_valid:
                        logger.info(f"Validation PASS: {output_path}")
                    else:
                        logger.warning(f"Validation FAIL: {output_path}")

                success += 1

            except Exception as e:
                logger.error(f"Error processing issue_id={issue_id}: {e}", exc_info=True)
                failures += 1
                continue

        print(f"Done: {success}/{total} files generated to {args.output_dir}/")

        if failures > 0:
            sys.exit(1)
        else:
            sys.exit(0)


if __name__ == "__main__":
    main()
