import argparse
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityEvaluator:
    def __init__(self):
        self.datasets = {}
        self.history = {}

    def register_dataset(self, name: str, df: pd.DataFrame, key_field: str = None):
        self.datasets[name] = {
            'df': df,
            'key_field': key_field,
            'loaded_at': datetime.utcnow().isoformat()
        }
        self.history[name] = []
        logger.info(f"Registered dataset: {name} ({len(df)} rows, {len(df.columns)} columns)")

    def evaluate_freshness(self, name: str, current_time: datetime = None) -> float:
        dataset = self.datasets[name]
        df = dataset['df']
        key_field = dataset['key_field']

        if key_field is None or key_field not in df.columns:
            return 1.0

        current_time = current_time or datetime.utcnow()

        try:
            latest_time = pd.to_datetime(df[key_field]).max()
            age_seconds = (current_time - latest_time).total_seconds()
            age_hours = age_seconds / 3600

            if age_hours <= 24:
                return 1.0
            elif age_hours <= 168:
                return 0.75
            elif age_hours <= 720:
                return 0.5
            else:
                return 0.0
        except Exception as e:
            logger.warning(f"Failed to evaluate freshness: {e}")
            return 0.5

    def evaluate_completeness(self, name: str) -> Dict[str, float]:
        df = self.datasets[name]['df']

        completeness = {}
        for col in df.columns:
            null_count = df[col].isnull().sum()
            completeness[col] = 1.0 - (null_count / len(df))

        overall = np.mean(list(completeness.values()))
        completeness['_overall'] = overall

        return completeness

    def evaluate_validity(self, name: str) -> Dict[str, Any]:
        df = self.datasets[name]['df']

        validity = {
            'total_rows': len(df),
            'duplicate_rows': df.duplicated().sum(),
            'column_count': len(df.columns),
            'dtypes': df.dtypes.to_dict()
        }

        duplicate_ratio = validity['duplicate_rows'] / len(df) if len(df) > 0 else 0
        validity['validity_score'] = 1.0 - min(duplicate_ratio, 1.0)

        return validity

    def evaluate_drift(self, name: str, baseline_stats: Dict = None) -> Dict[str, float]:
        df = self.datasets[name]['df']
        drift_scores = {}

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col in df.columns:
                current_mean = df[col].mean()
                current_std = df[col].std()

                if baseline_stats and col in baseline_stats:
                    baseline_mean = baseline_stats[col]['mean']
                    baseline_std = baseline_stats[col]['std']

                    z_score = abs(current_mean - baseline_mean) / (baseline_std + 1e-10)
                    drift_scores[col] = 1.0 - min(z_score / 3.0, 1.0)
                else:
                    drift_scores[col] = 1.0

        drift_scores['_overall'] = np.mean(list(drift_scores.values())) if drift_scores else 1.0

        return drift_scores

    def generate_report(self, name: str) -> Dict[str, Any]:
        logger.info(f"Generating quality report for {name}")

        freshness = self.evaluate_freshness(name)
        completeness = self.evaluate_completeness(name)
        validity = self.evaluate_validity(name)
        drift = self.evaluate_drift(name)

        overall_score = np.mean([
            freshness,
            completeness.get('_overall', 0.5),
            validity.get('validity_score', 0.5),
            drift.get('_overall', 0.5)
        ])

        report = {
            'dataset': name,
            'timestamp': datetime.utcnow().isoformat(),
            'overall_score': overall_score,
            'freshness': freshness,
            'completeness': {k: v for k, v in completeness.items() if isinstance(v, float)},
            'validity': {k: v for k, v in validity.items() if isinstance(v, (int, float))},
            'drift': {k: v for k, v in drift.items() if isinstance(v, float)},
            'status': 'good' if overall_score >= 0.8 else 'warning' if overall_score >= 0.6 else 'alert'
        }

        self.history[name].append(report)

        return report


def main():
    parser = argparse.ArgumentParser(description='Evaluate data quality')
    parser.add_argument('--dataset', required=True, help='Dataset name')
    parser.add_argument('--path', required=True, help='Data file path')
    parser.add_argument('--key-field', help='Timestamp/date field for freshness')
    parser.add_argument('--output', help='Output report file')

    args = parser.parse_args()

    df = pd.read_csv(args.path)
    evaluator = QualityEvaluator()
    evaluator.register_dataset(args.dataset, df, args.key_field)
    report = evaluator.generate_report(args.dataset)

    print(json.dumps(report, indent=2))

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report saved to {args.output}")


if __name__ == '__main__':
    main()
