"""
Configuration Service for fmem v3.1.0

Provides configuration from environment variables and config files.
Supports both the new ConfigService class and backward-compatible access.
"""

import os
import sys
import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple, Set


# Default values as module-level constants (preserved from ConfigManager)
DEFAULT_DATA_DIR = os.path.expanduser("~/.openclaw/memory")
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_INDEX_NAME = "faiss_index.fai"
DEFAULT_METADATA_NAME = "doc_metadata.json"
DEFAULT_SQLITE_NAME = "documents.db"

# Valid file extensions for indexing
_DEFAULT_VALID_EXTENSIONS = {'.md', '.txt', '.py', '.json', '.yaml', '.yml', '.csv'}

# Maximum file size (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024

# Maximum path length (4096 characters on most systems)
MAX_PATH_LENGTH = 1024

# Maximum query length
MAX_QUERY_LENGTH = 1000

# Maximum embedding content size (1MB)
MAX_EMBEDDING_SIZE = 1024 * 1024

# Maximum batch size
MAX_BATCH_SIZE = 100

# Maximum files to index per batch (0 = no limit)
DEFAULT_MAX_FILES_PER_BATCH = 0

# Memory quality enhancement settings
DEFAULT_ENABLE_RECENCY_RANKING = True
DEFAULT_RECENCY_WEIGHT = 0.3
DEFAULT_RECENCY_THRESHOLD_DAYS = 30
DEFAULT_MIN_RECENCY_SCORE = 0.1
DEFAULT_APPEND_ONLY_RECENCY_FACTOR = 0.33  # Reduce 30% → 10% for daily logs
DEFAULT_ENABLE_LOCATION_RANKING = True
DEFAULT_LOCATION_WEIGHT = 0.2

# Maximum chunk size for adaptive chunking (in characters)
# Overrides hardware-based auto-detection when set
DEFAULT_MAX_CHUNK_SIZE = None


@dataclass
class ConfigData:
    """Immutable configuration data container."""
    # Core paths
    data_dir: str
    ollama_url: str
    index_name: str
    metadata_name: str
    sqlite_name: str
    
    # File handling
    VALID_EXTENSIONS: Set[str]
    MAX_FILE_SIZE: int = MAX_FILE_SIZE
    MAX_PATH_LENGTH: int = MAX_PATH_LENGTH
    MAX_QUERY_LENGTH: int = MAX_QUERY_LENGTH
    MAX_EMBEDDING_SIZE: int = MAX_EMBEDDING_SIZE
    MAX_BATCH_SIZE: int = MAX_BATCH_SIZE
    
    # Directory indexing
    additional_dirs: str = ''
    exclude_dirs: str = ''
    index_files: str = ''
    index_memory_md: bool = True
    index_daily_files: bool = True
    
    # Memory quality enhancement
    enable_recency_ranking: bool = DEFAULT_ENABLE_RECENCY_RANKING
    recency_weight: float = DEFAULT_RECENCY_WEIGHT
    recency_threshold_days: int = DEFAULT_RECENCY_THRESHOLD_DAYS
    min_recency_score: float = DEFAULT_MIN_RECENCY_SCORE
    append_only_recency_factor: float = DEFAULT_APPEND_ONLY_RECENCY_FACTOR
    enable_location_ranking: bool = DEFAULT_ENABLE_LOCATION_RANKING
    location_weight: float = DEFAULT_LOCATION_WEIGHT
    
    # Chunking
    max_chunk_size: Optional[int] = DEFAULT_MAX_CHUNK_SIZE
    
    # Batch limits
    max_files_per_batch: int = DEFAULT_MAX_FILES_PER_BATCH
    
    # Rate limiting
    rate_limit_requests: int = 600
    rate_limit_window_seconds: int = 60
    
    # Embedding settings (from all-minilm:22m)
    embedding_dim: int = 384
    
    # Location-based importance weights
    location_weights: dict = field(default_factory=lambda: {
        'docs': 1.5,
        'documentation': 1.5,
        'projects': 1.3,
        'decisions': 1.4,
        'formal': 1.4,
        'work': 1.2,
        'active': 1.2,
        'current': 1.1,
        'notes': 1.0,
        'memory': 1.0,
        'chats': 0.8,
        'conversations': 0.8,
        'daily': 0.9,
        'sessions': 0.9,
        'base': 1.0,
    })
    
    @property
    def index_path(self) -> str:
        """Get full path to FAISS index file."""
        return os.path.join(self.data_dir, self.index_name)
    
    @property
    def metadata_path(self) -> str:
        """Get full path to metadata file."""
        return os.path.join(self.data_dir, self.metadata_name)
    
    @property
    def sqlite_path(self) -> str:
        """Get full path to SQLite database."""
        return os.path.join(self.data_dir, self.sqlite_name)
    
    def is_valid_extension(self, filepath: str) -> bool:
        """Check if file extension is in whitelist."""
        ext = Path(filepath).suffix.lower()
        return ext in self.VALID_EXTENSIONS
    
    def is_safe_path(self, filepath: str, base_dir: Optional[str] = None) -> bool:
        """Validate path to prevent path traversal attacks."""
        if not filepath:
            return False
        
        # Check path length
        if len(filepath) > self.MAX_PATH_LENGTH:
            return False
        
        # Normalize path
        try:
            resolved = Path(filepath).resolve()
        except (OSError, ValueError):
            return False
        
        # For absolute paths, require explicit base_dir
        # For relative paths, resolve relative to current dir is OK
        if Path(filepath).is_absolute():
            if base_dir is None:
                # Absolute paths need a base to validate against
                return False
            base_dir = Path(base_dir).resolve()
        else:
            # Relative paths are OK - resolve to current dir
            base_dir = Path.cwd()
        
        # Check if resolved path is within base directory
        try:
            resolved.relative_to(base_dir)
            return True
        except ValueError:
            return False
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate search query."""
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"
        
        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH} chars)"
        
        if len(query.strip()) == 0:
            return False, "Query cannot be whitespace only"
        
        return True, ""
    
    def validate_file_size(self, filepath: str) -> Tuple[bool, str]:
        """Validate file size."""
        try:
            size = os.path.getsize(filepath)
            if size > self.MAX_FILE_SIZE:
                return False, f"File too large (max {self.MAX_FILE_SIZE} bytes)"
            if size == 0:
                return False, "File is empty"
            return True, ""
        except OSError as e:
            return False, f"Cannot access file: {e}"


class ConfigService:
    """Loads and provides configuration. No longer a singleton."""
    
    def __init__(self, config_path: str = None):
        """Initialize configuration service.
        
        Args:
            config_path: Optional path to config file. If None, uses default location.
        """
        self._config_path = config_path
        self._config = self._load_config()
    
    def _load_config(self) -> ConfigData:
        """Load configuration from environment and config file.
        
        Returns:
            ConfigData: Loaded configuration data.
        """
        # Create a config parser for reading config file
        config = configparser.ConfigParser()
        
        # Environment variables take precedence
        data_dir = os.environ.get('FMEM_DATA_DIR', DEFAULT_DATA_DIR)
        ollama_url = os.environ.get('FMEM_OLLAMA_URL', DEFAULT_OLLAMA_URL)
        index_name = os.environ.get('FMEM_INDEX_NAME', DEFAULT_INDEX_NAME)
        metadata_name = os.environ.get('FMEM_METADATA_NAME', DEFAULT_METADATA_NAME)
        sqlite_name = os.environ.get('FMEM_SQLITE_NAME', DEFAULT_SQLITE_NAME)
        
        # Path to config file
        config_file_path = self._config_path or os.environ.get('FMEM_CONFIG', os.path.join(data_dir, 'fmem.conf'))
        
        # Initialize defaults
        additional_dirs = ''
        exclude_dirs = ''
        index_files = ''
        index_memory_md = True
        index_daily_files = True
        enable_recency_ranking = DEFAULT_ENABLE_RECENCY_RANKING
        recency_weight = DEFAULT_RECENCY_WEIGHT
        recency_threshold_days = DEFAULT_RECENCY_THRESHOLD_DAYS
        min_recency_score = DEFAULT_MIN_RECENCY_SCORE
        enable_location_ranking = DEFAULT_ENABLE_LOCATION_RANKING
        location_weight = DEFAULT_LOCATION_WEIGHT
        max_chunk_size = DEFAULT_MAX_CHUNK_SIZE
        max_files_per_batch = DEFAULT_MAX_FILES_PER_BATCH
        rate_limit_requests = 600
        rate_limit_window_seconds = 60
        valid_extensions = _DEFAULT_VALID_EXTENSIONS.copy()
        
        # Location-based importance weights for directories (defaults)
        location_weights = {
            'docs': 1.5,
            'documentation': 1.5,
            'projects': 1.3,
            'decisions': 1.4,
            'formal': 1.4,
            'work': 1.2,
            'active': 1.2,
            'current': 1.1,
            'notes': 1.0,
            'memory': 1.0,
            'chats': 0.8,
            'conversations': 0.8,
            'daily': 0.9,
            'sessions': 0.9,
            'base': 1.0,
        }
        
        if os.path.exists(config_file_path):
            try:
                config.read(config_file_path)
            except configparser.ParsingError as e:
                print(f"Warning: Config file '{config_file_path}' has syntax errors: {e}", file=sys.stderr)
                print("Using default configuration values.", file=sys.stderr)
                config = configparser.ConfigParser()
            except configparser.Error as e:
                print(f"Error: Could not read config file '{config_file_path}': {e}", file=sys.stderr)
                print("Using default configuration values.", file=sys.stderr)
                config = configparser.ConfigParser()
            except (IOError, OSError) as e:
                print(f"Error: Could not access config file '{config_file_path}': {e}", file=sys.stderr)
                print("Using default configuration values.", file=sys.stderr)
                config = configparser.ConfigParser()
            
            if 'settings' in config:
                try:
                    data_dir = os.path.expanduser(config.get('settings', 'data_dir', fallback=data_dir))
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                
                try:
                    ollama_url = config.get('settings', 'ollama_url', fallback=ollama_url)
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                
                # Directory indexing settings (all with graceful error handling)
                try:
                    additional_dirs = config.get('settings', 'additional_dirs', fallback='')
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                    
                try:
                    exclude_dirs = config.get('settings', 'exclude_dirs', fallback='')
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                    
                try:
                    index_files = config.get('settings', 'index_files', fallback='')
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                
                # Boolean values with error handling
                try:
                    index_memory_md = config.getboolean('settings', 'index_memory_md', fallback=True)
                except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
                    if isinstance(e, ValueError):
                        print(f"Warning: Invalid value for 'index_memory_md' in config, using default (True)", file=sys.stderr)
                    index_memory_md = True
                
                try:
                    index_daily_files = config.getboolean('settings', 'index_daily_files', fallback=True)
                except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
                    if isinstance(e, ValueError):
                        print(f"Warning: Invalid value for 'index_daily_files' in config, using default (True)", file=sys.stderr)
                    index_daily_files = True
                
                # File extensions to index
                try:
                    extensions_str = config.get('settings', 'extensions', fallback='.md, .txt, .py, .json, .yaml, .yml, .csv')
                    valid_extensions = {ext.strip() for ext in extensions_str.split(',') if ext.strip()}
                except (configparser.NoSectionError, configparser.NoOptionError):
                    pass
                
                # Memory quality enhancement settings with type validation
                try:
                    enable_recency_ranking = config.getboolean('settings', 'enable_recency_ranking', fallback=DEFAULT_ENABLE_RECENCY_RANKING)
                except ValueError:
                    print(f"Warning: Invalid boolean for 'enable_recency_ranking' in config, using default", file=sys.stderr)
                    enable_recency_ranking = DEFAULT_ENABLE_RECENCY_RANKING
                
                try:
                    recency_weight = config.getfloat('settings', 'recency_weight', fallback=DEFAULT_RECENCY_WEIGHT)
                    if not 0.0 <= recency_weight <= 1.0:
                        print(f"Warning: recency_weight should be between 0.0 and 1.0, got {recency_weight}", file=sys.stderr)
                        recency_weight = DEFAULT_RECENCY_WEIGHT
                except ValueError:
                    print(f"Warning: Invalid float for 'recency_weight' in config, using default", file=sys.stderr)
                    recency_weight = DEFAULT_RECENCY_WEIGHT
                
                try:
                    recency_threshold_days = config.getint('settings', 'recency_threshold_days', fallback=DEFAULT_RECENCY_THRESHOLD_DAYS)
                except ValueError:
                    print(f"Warning: Invalid integer for 'recency_threshold_days' in config, using default", file=sys.stderr)
                    recency_threshold_days = DEFAULT_RECENCY_THRESHOLD_DAYS
                
                try:
                    min_recency_score = config.getfloat('settings', 'min_recency_score', fallback=DEFAULT_MIN_RECENCY_SCORE)
                except ValueError:
                    print(f"Warning: Invalid float for 'min_recency_score' in config, using default", file=sys.stderr)
                    min_recency_score = DEFAULT_MIN_RECENCY_SCORE
                
                try:
                    append_only_recency_factor = config.getfloat('settings', 'append_only_recency_factor', fallback=DEFAULT_APPEND_ONLY_RECENCY_FACTOR)
                except ValueError:
                    print(f"Warning: Invalid float for 'append_only_recency_factor' in config, using default", file=sys.stderr)
                    append_only_recency_factor = DEFAULT_APPEND_ONLY_RECENCY_FACTOR
                
                # Location-based ranking settings
                try:
                    enable_location_ranking = config.getboolean('settings', 'enable_location_ranking', fallback=DEFAULT_ENABLE_LOCATION_RANKING)
                except ValueError:
                    print(f"Warning: Invalid boolean for 'enable_location_ranking' in config, using default", file=sys.stderr)
                    enable_location_ranking = DEFAULT_ENABLE_LOCATION_RANKING
                
                try:
                    location_weight = config.getfloat('settings', 'location_weight', fallback=DEFAULT_LOCATION_WEIGHT)
                    if not 0.0 <= location_weight <= 1.0:
                        print(f"Warning: location_weight should be between 0.0 and 1.0, got {location_weight}", file=sys.stderr)
                        location_weight = DEFAULT_LOCATION_WEIGHT
                except ValueError:
                    print(f"Warning: Invalid float for 'location_weight' in config, using default", file=sys.stderr)
                    location_weight = DEFAULT_LOCATION_WEIGHT
                
                # Chunking settings
                try:
                    max_chunk_val = config.getint('settings', 'max_chunk_size', fallback=0)
                    max_chunk_size = max_chunk_val if max_chunk_val > 0 else None
                except ValueError:
                    print(f"Warning: Invalid integer for 'max_chunk_size' in config, using default", file=sys.stderr)
                    max_chunk_size = None
                
                # Batch limits
                try:
                    max_files_per_batch = config.getint('settings', 'max_files_per_batch', fallback=DEFAULT_MAX_FILES_PER_BATCH)
                except ValueError:
                    print(f"Warning: Invalid integer for 'max_files_per_batch' in config, using default", file=sys.stderr)
                    max_files_per_batch = DEFAULT_MAX_FILES_PER_BATCH
                
                # Rate limiting settings
                try:
                    rate_limit_requests = config.getint('settings', 'rate_limit_requests', fallback=600)
                except ValueError:
                    print(f"Warning: Invalid integer for 'rate_limit_requests' in config, using default", file=sys.stderr)
                    rate_limit_requests = 600
                
                try:
                    rate_limit_window_seconds = config.getint('settings', 'rate_limit_window_seconds', fallback=60)
                except ValueError:
                    print(f"Warning: Invalid integer for 'rate_limit_window_seconds' in config, using default", file=sys.stderr)
                    rate_limit_window_seconds = 60
                
                # Location-based importance weights for directories
                location_weight_keys = {
                    'docs': 1.5, 'documentation': 1.5, 'projects': 1.3, 'decisions': 1.4,
                    'formal': 1.4, 'work': 1.2, 'active': 1.2, 'current': 1.1,
                    'notes': 1.0, 'memory': 1.0, 'chats': 0.8, 'conversations': 0.8,
                    'daily': 0.9, 'sessions': 0.9, 'base': 1.0
                }
                location_weights = {}
                for key, default_val in location_weight_keys.items():
                    try:
                        location_weights[key] = config.getfloat('settings', f'{key}_weight', fallback=default_val)
                    except ValueError:
                        print(f"Warning: Invalid float for '{key}_weight' in config, using default", file=sys.stderr)
                        location_weights[key] = default_val
                        
            else:
                if config.sections():
                    print(f"Warning: Config file '{config_file_path}' missing [settings] section", file=sys.stderr)
                    print("Using default configuration values.", file=sys.stderr)
                else:
                    print(f"Warning: Config file '{config_file_path}' is empty or has no sections", file=sys.stderr)
                    print("Using default configuration values.", file=sys.stderr)
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Return ConfigData with all loaded values
        return ConfigData(
            data_dir=data_dir,
            ollama_url=ollama_url,
            index_name=index_name,
            metadata_name=metadata_name,
            sqlite_name=sqlite_name,
            VALID_EXTENSIONS=valid_extensions,
            additional_dirs=additional_dirs,
            exclude_dirs=exclude_dirs,
            index_files=index_files,
            index_memory_md=index_memory_md,
            index_daily_files=index_daily_files,
            enable_recency_ranking=enable_recency_ranking,
            recency_weight=recency_weight,
            recency_threshold_days=recency_threshold_days,
            min_recency_score=min_recency_score,
            append_only_recency_factor=append_only_recency_factor if 'append_only_recency_factor' in dir() else DEFAULT_APPEND_ONLY_RECENCY_FACTOR,
            enable_location_ranking=enable_location_ranking,
            location_weight=location_weight,
            max_chunk_size=max_chunk_size,
            max_files_per_batch=max_files_per_batch,
            rate_limit_requests=rate_limit_requests,
            rate_limit_window_seconds=rate_limit_window_seconds,
            location_weights=location_weights,
        )
    
    @property
    def config_data(self) -> ConfigData:
        """Get the configuration data.
        
        Returns:
            ConfigData: The loaded configuration.
        """
        return self._config
    
    def get_config(self) -> ConfigData:
        """Get the configuration data (alias for config_data property).
        
        Returns:
            ConfigData: The loaded configuration.
        """
        return self._config
    
    # Delegate methods to config_data for backward compatibility
    @property
    def index_path(self) -> str:
        """Get full path to FAISS index file."""
        return self._config.index_path
    
    @property
    def metadata_path(self) -> str:
        """Get full path to metadata file."""
        return self._config.metadata_path
    
    @property
    def sqlite_path(self) -> str:
        """Get full path to SQLite database."""
        return self._config.sqlite_path
    
    @property
    def data_dir(self) -> str:
        """Get data directory."""
        return self._config.data_dir
    
    @property
    def ollama_url(self) -> str:
        """Get Ollama URL."""
        return self._config.ollama_url
    
    @property
    def index_name(self) -> str:
        """Get index name."""
        return self._config.index_name
    
    @property
    def metadata_name(self) -> str:
        """Get metadata name."""
        return self._config.metadata_name
    
    @property
    def sqlite_name(self) -> str:
        """Get SQLite name."""
        return self._config.sqlite_name
    
    @property
    def embedding_dim(self) -> int:
        """Get embedding dimension (from all-minilm:22m model)."""
        return self._config.embedding_dim
    
    @property
    def VALID_EXTENSIONS(self) -> Set[str]:
        """Get valid file extensions."""
        return self._config.VALID_EXTENSIONS
    
    @property
    def additional_dirs(self) -> str:
        """Get additional directories."""
        return self._config.additional_dirs
    
    @property
    def exclude_dirs(self) -> str:
        """Get exclude directories."""
        return self._config.exclude_dirs
    
    @property
    def index_files(self) -> str:
        """Get index files."""
        return self._config.index_files
    
    @property
    def index_memory_md(self) -> bool:
        """Get index_memory_md setting."""
        return self._config.index_memory_md
    
    @property
    def index_daily_files(self) -> bool:
        """Get index_daily_files setting."""
        return self._config.index_daily_files
    
    @property
    def enable_recency_ranking(self) -> bool:
        """Get enable_recency_ranking setting."""
        return self._config.enable_recency_ranking
    
    @property
    def recency_weight(self) -> float:
        """Get recency_weight setting."""
        return self._config.recency_weight
    
    @property
    def recency_threshold_days(self) -> int:
        """Get recency_threshold_days setting."""
        return self._config.recency_threshold_days
    
    @property
    def min_recency_score(self) -> float:
        """Get min_recency_score setting."""
        return self._config.min_recency_score
    
    @property
    def append_only_recency_factor(self) -> float:
        """Get append_only_recency_factor setting."""
        return self._config.append_only_recency_factor
    
    @property
    def enable_location_ranking(self) -> bool:
        """Get enable_location_ranking setting."""
        return self._config.enable_location_ranking
    
    @property
    def location_weight(self) -> float:
        """Get location_weight setting."""
        return self._config.location_weight
    
    @property
    def max_chunk_size(self) -> Optional[int]:
        """Get max_chunk_size setting."""
        return self._config.max_chunk_size
    
    @property
    def max_files_per_batch(self) -> int:
        """Get max_files_per_batch setting."""
        return self._config.max_files_per_batch
    
    @property
    def rate_limit_requests(self) -> int:
        """Get rate_limit_requests setting."""
        return self._config.rate_limit_requests
    
    @property
    def rate_limit_window_seconds(self) -> int:
        """Get rate_limit_window_seconds setting."""
        return self._config.rate_limit_window_seconds
    
    @property
    def location_weights(self) -> dict:
        """Get location_weights setting."""
        return self._config.location_weights
    
    @property
    def MAX_FILE_SIZE(self) -> int:
        """Get max file size limit."""
        return self._config.MAX_FILE_SIZE
    
    @property
    def MAX_PATH_LENGTH(self) -> int:
        """Get max path length limit."""
        return self._config.MAX_PATH_LENGTH
    
    def is_valid_extension(self, filepath: str) -> bool:
        """Check if file extension is in whitelist."""
        return self._config.is_valid_extension(filepath)
    
    def is_safe_path(self, filepath: str, base_dir: Optional[str] = None) -> bool:
        """Validate path to prevent path traversal attacks."""
        return self._config.is_safe_path(filepath, base_dir)
    
    def validate_query(self, query: str) -> Tuple[bool, str]:
        """Validate search query."""
        return self._config.validate_query(query)
    
    def validate_file_size(self, filepath: str) -> Tuple[bool, str]:
        """Validate file size."""
        return self._config.validate_file_size(filepath)


# Global singleton instance for backward compatibility
_config_service_instance = None


def get_config() -> ConfigData:
    """Backward-compatible global config access.
    
    Returns:
        ConfigData: The global configuration data.
    """
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance.get_config()
