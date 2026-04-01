import logging
from lxml import etree


logger = logging.getLogger(__name__)


def validate_xml(xml_path: str, xsd_path: str) -> bool:
    """
    Validate an XML file against an XSD schema using lxml.
    
    Args:
        xml_path: Path to the XML file to validate
        xsd_path: Path to the XSD schema file
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Load XSD schema
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f)
        schema = etree.XMLSchema(schema_doc)

        # Parse XML file
        with open(xml_path, 'rb') as f:
            xml_doc = etree.parse(f)

        # Validate
        is_valid = schema.validate(xml_doc)

        if not is_valid:
            for error in schema.error_log:
                logger.error(f"Line {error.line}: {error.message}")
            return False

        # If valid
        logger.info(f"XML is valid: {xml_path}")
        return True

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return False


def validate_xml_string(xml_string: str, xsd_path: str) -> bool:
    """
    Validate an XML string against an XSD schema using lxml.
    
    Args:
        xml_string: XML content as string to validate
        xsd_path: Path to the XSD schema file
    
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Load XSD schema
        with open(xsd_path, 'rb') as f:
            schema_doc = etree.parse(f)
        schema = etree.XMLSchema(schema_doc)

        # Parse XML string
        xml_doc = etree.fromstring(xml_string.encode('utf-8'))

        # Validate
        is_valid = schema.validate(xml_doc)

        if not is_valid:
            for error in schema.error_log:
                logger.error(f"Line {error.line}: {error.message}")
            return False

        # If valid
        logger.info("XML string is valid")
        return True

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except etree.XMLSyntaxError as e:
        logger.error(f"XML syntax error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during validation: {e}")
        return False