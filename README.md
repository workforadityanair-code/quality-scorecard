# Data Quality Scorecard

Automated data quality monitoring with freshness, completeness, and drift detection.

## Features

- Measures data freshness (staleness detection)
- Completeness scoring (null/missing value analysis)
- Distribution drift detection (statistical tests)
- Schema validation and anomaly detection
- Real-time alerting on quality degradation
- Historical tracking and trend analysis
- Multi-dataset support with aggregation
- Exportable reports (JSON, CSV)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Register a dataset:

```bash
python register.py --name sales_data --path data/sales.csv --key_field date --config config.yaml
```

Run quality checks:

```bash
python evaluate.py --dataset sales_data --output report.json
```

View scorecard:

```bash
python scorecard.py --dataset sales_data
```

Monitor with alerts:

```bash
python monitor.py --datasets sales_data,inventory_data --alert-threshold 0.7 --interval 3600
```

## Metrics

Each dataset gets a score 0-1:
- Freshness: How recent is the data
- Completeness: Percentage of non-null values
- Validity: Schema conformance
- Consistency: Cross-table relationships
- Distribution: Statistical tests for drift

## Output

Generates detailed reports with drill-down by column, field-level issues, and trend analysis.
