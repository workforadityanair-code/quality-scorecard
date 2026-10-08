import argparse
import json
import logging
import time
import pandas as pd
from datetime import datetime
from typing import List, Dict
from evaluate import QualityEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QualityMonitor:
    def __init__(self, alert_threshold: float = 0.7):
        self.alert_threshold = alert_threshold
        self.evaluator = QualityEvaluator()
        self.alerts = []

    def load_dataset(self, name: str, path: str, key_field: str = None):
        df = pd.read_csv(path)
        self.evaluator.register_dataset(name, df, key_field)

    def check_dataset(self, name: str) -> Dict:
        report = self.evaluator.generate_report(name)

        if report['overall_score'] < self.alert_threshold:
            alert = {
                'timestamp': report['timestamp'],
                'dataset': name,
                'severity': 'critical' if report['overall_score'] < 0.5 else 'warning',
                'score': report['overall_score'],
                'issues': []
            }

            if report['freshness'] < 0.7:
                alert['issues'].append('Data freshness degraded')

            for col, score in report['completeness'].items():
                if col != '_overall' and score < 0.9:
                    alert['issues'].append(f"Column {col} missing {(1-score)*100:.1f}% values")

            if report['validity']['validity_score'] < 0.8:
                alert['issues'].append('High duplicate row count')

            self.alerts.append(alert)
            logger.warning(f"Alert: {name} score dropped to {report['overall_score']:.2f}")
            return alert

        return None

    def run_continuous(self, datasets: Dict[str, str], interval: int = 3600):
        logger.info(f"Starting continuous monitoring (interval: {interval}s)")

        for name, path in datasets.items():
            self.load_dataset(name, path)

        iteration = 0
        while True:
            iteration += 1
            logger.info(f"Monitoring iteration {iteration} at {datetime.utcnow()}")

            for name in datasets.keys():
                self.check_dataset(name)

            logger.info(f"Active alerts: {len([a for a in self.alerts if a['severity'] == 'critical'])}")

            time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description='Monitor data quality')
    parser.add_argument('--datasets', nargs='+', required=True, help='Dataset paths (name:path)')
    parser.add_argument('--alert-threshold', type=float, default=0.7, help='Alert threshold score')
    parser.add_argument('--interval', type=int, default=3600, help='Check interval in seconds')
    parser.add_argument('--output', help='Output alerts file')

    args = parser.parse_args()

    datasets = {}
    for dataset_spec in args.datasets:
        name, path = dataset_spec.split(':')
        datasets[name] = path

    monitor = QualityMonitor(args.alert_threshold)

    if len(datasets) == 1:
        for name, path in datasets.items():
            monitor.load_dataset(name, path)
            alert = monitor.check_dataset(name)

            if alert:
                print(json.dumps(alert, indent=2))
            else:
                print(f"Dataset {name}: Quality score GOOD")

            if args.output:
                with open(args.output, 'w') as f:
                    json.dump(monitor.alerts, f, indent=2)
    else:
        monitor.run_continuous(datasets, args.interval)


if __name__ == '__main__':
    main()
