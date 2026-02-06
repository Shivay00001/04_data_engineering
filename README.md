# 04_data_engineering - ETL Pipeline

> Production-grade data engineering pipeline demonstrating modern ETL patterns with batch and streaming capabilities.

## 🎯 Overview

This module implements enterprise data engineering:

- **ETL Pipeline** - Extract, Transform, Load patterns
- **Data Quality** - Validation and profiling
- **Orchestration** - Job scheduling and DAGs
- **Connectors** - Database, API, file sources

## 📁 Structure

```
04_data_engineering/
├── src/
│   ├── extractors/          # Data extraction
│   │   ├── database.py      # SQL sources
│   │   ├── api.py           # REST API sources
│   │   └── file.py          # File sources
│   ├── transformers/        # Data transformation
│   │   ├── cleaning.py      # Data cleaning
│   │   ├── validation.py    # Data validation
│   │   └── enrichment.py    # Data enrichment
│   ├── loaders/             # Data loading
│   │   ├── database.py      # Database sinks
│   │   └── warehouse.py     # Data warehouse
│   ├── pipeline/            # Pipeline orchestration
│   │   ├── runner.py        # Pipeline runner
│   │   └── scheduler.py     # Job scheduling
│   └── quality/             # Data quality
│       ├── profiler.py      # Data profiling
│       └── checks.py        # Quality checks
├── tests/                   # Test suite
└── example_data/            # Sample data
```

## 🚀 Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e .

# Run example pipeline
python -m src.main
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       DATA SOURCES                          │
│          Databases │ APIs │ Files │ Streams                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      EXTRACTORS                             │
│            DatabaseExtractor │ APIExtractor                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     TRANSFORMERS                            │
│         Cleaning │ Validation │ Enrichment                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       LOADERS                               │
│           Database │ Warehouse │ Files                      │
└─────────────────────────────────────────────────────────────┘
```

## 📄 License

MIT
