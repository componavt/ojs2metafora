from pathlib import Path
from src.sources import SOURCES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PROJECT_ROOT / "output"


def get_output_namespace(source_key: str) -> str:
    """
    Return the output namespace for a given source key.
    
    Args:
        source_key: Key from SOURCES dict (e.g., 'karrc', 'mgta')
    
    Returns:
        The output_namespace value for the source.
    
    Raises:
        ValueError: If source_key is not found in SOURCES.
    """
    if source_key not in SOURCES:
        available = ', '.join(sorted(SOURCES.keys()))
        raise ValueError(
            f"Unknown source key '{source_key}'. Available sources: {available}"
        )
    return SOURCES[source_key]["output_namespace"]


def default_output_dir(source_key: str) -> Path:
    """
    Return the default output directory for a source (output/<namespace>).
    
    Args:
        source_key: Key from SOURCES dict (e.g., 'karrc', 'mgta')
    
    Returns:
        Path to output/<namespace> directory.
    """
    return OUTPUT_ROOT / get_output_namespace(source_key)


def resolve_generation_output_dir(
    source_key: str,
    explicit_output_dir: str | None,
) -> Path:
    """
    Resolve the output directory for XML generation commands.
    
    If explicit_output_dir is provided, it is used literally without appending
    the source namespace or any year. If None, the source-specific default
    directory is returned.
    
    Args:
        source_key: Key from SOURCES dict (e.g., 'karrc', 'mgta')
        explicit_output_dir: Path supplied via --output-dir CLI arg, or None.
    
    Returns:
        Path object for the output directory.
    """
    if explicit_output_dir is not None:
        return Path(explicit_output_dir)
    return default_output_dir(source_key)


def resolve_batch_output_dir(
    source_key: str,
    year_or_directory: str,
) -> Path:
    """
    Resolve the output directory for Metafora batch commands.
    
    If year_or_directory is an existing directory, it is used literally
    regardless of source_key. Otherwise, it is treated as a year token
    and combined with the source's default output directory.
    
    Args:
        source_key: Key from SOURCES dict (e.g., 'karrc', 'mgta')
        year_or_directory: Year string (e.g., '2022') or directory path.
    
    Returns:
        Path for the batch operation base directory.
    """
    path = Path(year_or_directory)
    if path.is_dir():
        return path
    return default_output_dir(source_key) / year_or_directory


def get_upload_log_path(source_key: str) -> Path:
    """
    Return the source-specific upload-log file path.

    This function only resolves a path. It must not create directories or
    files.
    
    Args:
        source_key: Key from SOURCES dict (e.g., 'karrc', 'mgta')
    
    Returns:
        Path to output/<namespace>/upload_log.json
    """
    return default_output_dir(source_key) / "upload_log.json"
