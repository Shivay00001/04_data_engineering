"""
Data Transformers - Transform and validate data.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd


@dataclass
class TransformResult:
    """Result of transformation."""
    
    data: pd.DataFrame
    original_count: int
    transformed_count: int
    dropped_count: int = 0
    errors: List[str] = field(default_factory=list)


class BaseTransformer(ABC):
    """Abstract base class for data transformers."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def transform(self, df: pd.DataFrame) -> TransformResult:
        """Transform the data."""
        pass


class CleaningTransformer(BaseTransformer):
    """Clean and standardize data."""
    
    def __init__(
        self,
        name: str = "cleaner",
        drop_duplicates: bool = True,
        drop_null_columns: Optional[List[str]] = None,
        fill_null_values: Optional[Dict[str, Any]] = None,
        strip_whitespace: bool = True,
        lowercase_columns: Optional[List[str]] = None,
    ):
        super().__init__(name)
        self.drop_duplicates = drop_duplicates
        self.drop_null_columns = drop_null_columns or []
        self.fill_null_values = fill_null_values or {}
        self.strip_whitespace = strip_whitespace
        self.lowercase_columns = lowercase_columns or []
    
    def transform(self, df: pd.DataFrame) -> TransformResult:
        """Apply cleaning transformations."""
        original_count = len(df)
        result_df = df.copy()
        errors = []
        
        # Drop duplicates
        if self.drop_duplicates:
            result_df = result_df.drop_duplicates()
        
        # Drop rows with null in required columns
        for col in self.drop_null_columns:
            if col in result_df.columns:
                result_df = result_df.dropna(subset=[col])
        
        # Fill null values
        for col, value in self.fill_null_values.items():
            if col in result_df.columns:
                result_df[col] = result_df[col].fillna(value)
        
        # Strip whitespace from string columns
        if self.strip_whitespace:
            string_cols = result_df.select_dtypes(include=["object"]).columns
            for col in string_cols:
                result_df[col] = result_df[col].str.strip()
        
        # Lowercase specified columns
        for col in self.lowercase_columns:
            if col in result_df.columns:
                result_df[col] = result_df[col].str.lower()
        
        return TransformResult(
            data=result_df,
            original_count=original_count,
            transformed_count=len(result_df),
            dropped_count=original_count - len(result_df),
            errors=errors,
        )


class ValidationTransformer(BaseTransformer):
    """Validate data against rules."""
    
    def __init__(
        self,
        name: str = "validator",
        required_columns: Optional[List[str]] = None,
        column_types: Optional[Dict[str, str]] = None,
        value_ranges: Optional[Dict[str, tuple]] = None,
        allowed_values: Optional[Dict[str, List[Any]]] = None,
        drop_invalid: bool = False,
    ):
        super().__init__(name)
        self.required_columns = required_columns or []
        self.column_types = column_types or {}
        self.value_ranges = value_ranges or {}
        self.allowed_values = allowed_values or {}
        self.drop_invalid = drop_invalid
    
    def transform(self, df: pd.DataFrame) -> TransformResult:
        """Validate data and optionally drop invalid rows."""
        original_count = len(df)
        result_df = df.copy()
        errors = []
        valid_mask = pd.Series([True] * len(df))
        
        # Check required columns
        for col in self.required_columns:
            if col not in df.columns:
                errors.append(f"Missing required column: {col}")
        
        # Validate column types
        for col, expected_type in self.column_types.items():
            if col in df.columns:
                try:
                    if expected_type == "numeric":
                        pd.to_numeric(df[col], errors="raise")
                    elif expected_type == "datetime":
                        pd.to_datetime(df[col], errors="raise")
                except Exception:
                    errors.append(f"Invalid type in column {col}: expected {expected_type}")
                    if self.drop_invalid:
                        valid_mask &= pd.to_numeric(df[col], errors="coerce").notna()
        
        # Validate value ranges
        for col, (min_val, max_val) in self.value_ranges.items():
            if col in df.columns:
                col_values = pd.to_numeric(df[col], errors="coerce")
                out_of_range = (col_values < min_val) | (col_values > max_val)
                if out_of_range.any():
                    errors.append(f"Values out of range in {col}: [{min_val}, {max_val}]")
                    if self.drop_invalid:
                        valid_mask &= ~out_of_range
        
        # Validate allowed values
        for col, allowed in self.allowed_values.items():
            if col in df.columns:
                invalid = ~df[col].isin(allowed)
                if invalid.any():
                    errors.append(f"Invalid values in {col}")
                    if self.drop_invalid:
                        valid_mask &= ~invalid
        
        if self.drop_invalid:
            result_df = result_df[valid_mask]
        
        return TransformResult(
            data=result_df,
            original_count=original_count,
            transformed_count=len(result_df),
            dropped_count=original_count - len(result_df),
            errors=errors,
        )


class EnrichmentTransformer(BaseTransformer):
    """Enrich data with derived columns."""
    
    def __init__(
        self,
        name: str = "enricher",
        computed_columns: Optional[Dict[str, Callable]] = None,
        date_parts: Optional[Dict[str, str]] = None,
        categories: Optional[Dict[str, List[tuple]]] = None,
    ):
        super().__init__(name)
        self.computed_columns = computed_columns or {}
        self.date_parts = date_parts or {}
        self.categories = categories or {}
    
    def transform(self, df: pd.DataFrame) -> TransformResult:
        """Apply enrichment transformations."""
        original_count = len(df)
        result_df = df.copy()
        errors = []
        
        # Add computed columns
        for col_name, func in self.computed_columns.items():
            try:
                result_df[col_name] = result_df.apply(func, axis=1)
            except Exception as e:
                errors.append(f"Error computing {col_name}: {e}")
        
        # Extract date parts
        for source_col, parts in self.date_parts.items():
            if source_col in result_df.columns:
                try:
                    dt = pd.to_datetime(result_df[source_col])
                    if "year" in parts:
                        result_df[f"{source_col}_year"] = dt.dt.year
                    if "month" in parts:
                        result_df[f"{source_col}_month"] = dt.dt.month
                    if "day" in parts:
                        result_df[f"{source_col}_day"] = dt.dt.day
                    if "day_of_week" in parts:
                        result_df[f"{source_col}_dow"] = dt.dt.dayofweek
                except Exception as e:
                    errors.append(f"Error extracting date parts from {source_col}: {e}")
        
        return TransformResult(
            data=result_df,
            original_count=original_count,
            transformed_count=len(result_df),
            errors=errors,
        )


class Pipeline:
    """Chain multiple transformers together."""
    
    def __init__(self, transformers: List[BaseTransformer]):
        self.transformers = transformers
    
    def run(self, df: pd.DataFrame) -> TransformResult:
        """Run all transformers in sequence."""
        current_df = df
        all_errors = []
        total_dropped = 0
        
        for transformer in self.transformers:
            result = transformer.transform(current_df)
            current_df = result.data
            all_errors.extend(result.errors)
            total_dropped += result.dropped_count
        
        return TransformResult(
            data=current_df,
            original_count=len(df),
            transformed_count=len(current_df),
            dropped_count=total_dropped,
            errors=all_errors,
        )
