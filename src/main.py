# Example usage:
# python main.py 151
# python main.py 151 --titleid 38962 --validate --verbose

import argparse
import logging
import os
import sys
from pathlib import Path

import sys
from pathlib import Path

# Add the src directory to the path to allow imports
sys.path.append(str(Path(__file__).parent))

from issue_builder import build_journal_xml, SERIES_MAP


def main():
    parser = argparse.ArgumentParser(description='Export OJS issue to Metafora XML format')
    parser.add_argument('issue_id', type=int, help='Integer ID of the OJS issue to export')
    parser.add_argument('--output-dir', default='output', help='Directory for output files (default: output)')
    parser.add_argument('--titleid', default='', help='Metaphora titleid value for <titleid> element')
    parser.add_argument('--validate', action='store_true', help='Validate the output XML against journal3.xsd')
    parser.add_argument('--verbose', action='store_true', help='Enable DEBUG-level logging')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Ensure schemas directory exists and journal3.xsd is present
        schemas_dir = Path(__file__).parent.parent / 'schemas'
        xsd_path = str(schemas_dir / 'journal3.xsd')
        if args.validate and not Path(xsd_path).exists():
            # Try relative path as fallback
            xsd_path = 'schemas/journal3.xsd'
        
        # Build the journal XML
        tree, meta = build_journal_xml(args.issue_id, titleid=args.titleid)
        
        series_name = SERIES_MAP.get(meta.get('journal_path', ''), meta.get('journal_path', 'unknown'))
        year = meta.get('year', 'unknown')
        number = meta.get('number', '0')
        
        # Create year directory
        year_dir = Path(args.output_dir) / year
        year_dir.mkdir(parents=True, exist_ok=True)
        
        # Define output path with year and series name
        output_path = year_dir / f'{series_name}_n{number}.xml'
        
        # Write XML to file
        tree.write(
            str(output_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )
        
        print(f"XML saved: {output_path}")
        
        # Validate if requested
        if args.validate:
            from validator import validate_xml
            is_valid = validate_xml(str(output_path), xsd_path)
            
            if is_valid:
                print("Validation: OK")
            else:
                print("Validation failed")
                sys.exit(1)
    
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(2)


if __name__ == "__main__":
    main()
