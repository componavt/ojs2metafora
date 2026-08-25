from src.sources import SOURCES


def get_adapter(source_key: str):
    """
    Factory function that returns an adapter instance for the given source key.
    
    Args:
        source_key: The key identifying the source profile (e.g., "karrc", "mgta").
    
    Returns:
        An instance of the appropriate adapter class (e.g., Ojs24Adapter).
    
    Raises:
        ValueError: If source_key is unknown.
        NotImplementedError: If the adapter for the source is not yet implemented.
    """
    if source_key not in SOURCES:
        available = ", ".join(sorted(SOURCES.keys()))
        raise ValueError(
            f"Unknown source key '{source_key}'. Available sources: {available}"
        )
    
    profile = SOURCES[source_key]
    adapter_key = profile.get("adapter")
    
    if adapter_key == "ojs24":
        from src.adapters.ojs24 import Ojs24Adapter
        return Ojs24Adapter(source_key)
    elif adapter_key == "ojs31":
        from src.adapters.ojs31 import Ojs31Adapter
        return Ojs31Adapter(source_key)
    else:
        raise NotImplementedError(
            f"Adapter '{adapter_key}' for source '{source_key}' is not supported"
        )
