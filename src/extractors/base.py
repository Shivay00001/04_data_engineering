"""
Base Extractor - Abstract data extraction interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, TypeVar

import pandas as pd


@dataclass
class ExtractionResult:
    """Result of data extraction."""
    
    data: pd.DataFrame
    source: str
    extracted_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    record_count: int = 0
    
    def __post_init__(self):
        self.record_count = len(self.data)


class BaseExtractor(ABC):
    """Abstract base class for data extractors."""
    
    def __init__(self, name: str):
        """
        Initialize extractor.
        
        Args:
            name: Extractor name for logging
        """
        self.name = name
        self._logger = self._get_logger()
    
    def _get_logger(self):
        """Get structured logger."""
        try:
            import structlog
            return structlog.get_logger(self.name)
        except ImportError:
            import logging
            return logging.getLogger(self.name)
    
    @abstractmethod
    def extract(self) -> ExtractionResult:
        """
        Extract data from source.
        
        Returns:
            Extraction result with DataFrame
        """
        pass
    
    def extract_incremental(
        self,
        since: Optional[datetime] = None,
    ) -> ExtractionResult:
        """
        Extract data incrementally since last extraction.
        
        Args:
            since: Timestamp to extract from
            
        Returns:
            Extraction result
        """
        # Default implementation calls full extract
        return self.extract()
    
    def validate(self, result: ExtractionResult) -> bool:
        """
        Validate extraction result.
        
        Args:
            result: Extraction result to validate
            
        Returns:
            True if valid
        """
        return len(result.data) > 0


class DatabaseExtractor(BaseExtractor):
    """Extract data from SQL databases."""
    
    def __init__(
        self,
        name: str,
        connection_string: str,
        query: str,
        params: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize database extractor.
        
        Args:
            name: Extractor name
            connection_string: Database connection string
            query: SQL query to execute
            params: Optional query parameters
        """
        super().__init__(name)
        self.connection_string = connection_string
        self.query = query
        self.params = params or {}
    
    def extract(self) -> ExtractionResult:
        """Extract data from database."""
        self._logger.info("Extracting data", query=self.query[:100])
        
        df = pd.read_sql(
            self.query,
            self.connection_string,
            params=self.params,
        )
        
        return ExtractionResult(
            data=df,
            source=f"database:{self.name}",
            metadata={
                "query": self.query,
                "params": self.params,
            },
        )
    
    def extract_incremental(
        self,
        since: Optional[datetime] = None,
        timestamp_column: str = "updated_at",
    ) -> ExtractionResult:
        """Extract data incrementally using timestamp column."""
        if since:
            incremental_query = f"""
                SELECT * FROM ({self.query}) AS base
                WHERE {timestamp_column} > :since
            """
            params = {**self.params, "since": since}
        else:
            incremental_query = self.query
            params = self.params
        
        df = pd.read_sql(incremental_query, self.connection_string, params=params)
        
        return ExtractionResult(
            data=df,
            source=f"database:{self.name}",
            metadata={
                "incremental": True,
                "since": since.isoformat() if since else None,
            },
        )


class APIExtractor(BaseExtractor):
    """Extract data from REST APIs."""
    
    def __init__(
        self,
        name: str,
        base_url: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        pagination_key: Optional[str] = None,
    ):
        """
        Initialize API extractor.
        
        Args:
            name: Extractor name
            base_url: API base URL
            endpoint: API endpoint
            headers: Request headers
            params: Query parameters
            pagination_key: Key for pagination
        """
        super().__init__(name)
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint.lstrip("/")
        self.headers = headers or {}
        self.params = params or {}
        self.pagination_key = pagination_key
    
    def extract(self) -> ExtractionResult:
        """Extract data from API."""
        import httpx
        
        url = f"{self.base_url}/{self.endpoint}"
        all_data = []
        
        self._logger.info("Extracting from API", url=url)
        
        with httpx.Client() as client:
            params = self.params.copy()
            
            while True:
                response = client.get(
                    url,
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, list):
                    all_data.extend(data)
                    break
                elif isinstance(data, dict):
                    items = data.get("data", data.get("items", data.get("results", [])))
                    all_data.extend(items)
                    
                    # Handle pagination
                    if self.pagination_key and data.get(self.pagination_key):
                        params["cursor"] = data[self.pagination_key]
                    else:
                        break
        
        df = pd.DataFrame(all_data)
        
        return ExtractionResult(
            data=df,
            source=f"api:{self.name}",
            metadata={"url": url},
        )


class FileExtractor(BaseExtractor):
    """Extract data from files."""
    
    SUPPORTED_FORMATS = ["csv", "json", "parquet", "excel"]
    
    def __init__(
        self,
        name: str,
        file_path: str,
        file_format: Optional[str] = None,
        **read_options,
    ):
        """
        Initialize file extractor.
        
        Args:
            name: Extractor name
            file_path: Path to file
            file_format: File format (auto-detected if not specified)
            **read_options: Additional pandas read options
        """
        super().__init__(name)
        self.file_path = file_path
        self.file_format = file_format or self._detect_format(file_path)
        self.read_options = read_options
    
    def _detect_format(self, path: str) -> str:
        """Detect file format from extension."""
        ext = path.rsplit(".", 1)[-1].lower()
        if ext in ["xlsx", "xls"]:
            return "excel"
        return ext
    
    def extract(self) -> ExtractionResult:
        """Extract data from file."""
        self._logger.info("Extracting from file", path=self.file_path)
        
        if self.file_format == "csv":
            df = pd.read_csv(self.file_path, **self.read_options)
        elif self.file_format == "json":
            df = pd.read_json(self.file_path, **self.read_options)
        elif self.file_format == "parquet":
            df = pd.read_parquet(self.file_path, **self.read_options)
        elif self.file_format == "excel":
            df = pd.read_excel(self.file_path, **self.read_options)
        else:
            raise ValueError(f"Unsupported format: {self.file_format}")
        
        return ExtractionResult(
            data=df,
            source=f"file:{self.file_path}",
            metadata={
                "format": self.file_format,
                "path": self.file_path,
            },
        )
