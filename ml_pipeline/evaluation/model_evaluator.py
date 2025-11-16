"""Model evaluation and monitoring."""
import pandas as pd
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    roc_auc_score,
    confusion_matrix
)
import json
from datetime import datetime


class ModelEvaluator:
    """Evaluates and monitors ML model performance."""

    def evaluate_classifier(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_pred_proba: np.ndarray | None = None
    ) -> dict:
        """
        Comprehensive classifier evaluation.

        Args:
            y_true: True labels
            y_pred: Predicted labels
            y_pred_proba: Prediction probabilities (optional)

        Returns:
            Evaluation metrics
        """
        metrics = {}

        # Basic metrics
        metrics['accuracy'] = float(accuracy_score(y_true, y_pred))

        # Precision, recall, F1
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, average='binary'
        )

        metrics['precision'] = float(precision)
        metrics['recall'] = float(recall)
        metrics['f1_score'] = float(f1)

        # ROC AUC if probabilities provided
        if y_pred_proba is not None:
            metrics['roc_auc'] = float(roc_auc_score(y_true, y_pred_proba))

        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = {
            'true_negatives': int(cm[0, 0]),
            'false_positives': int(cm[0, 1]),
            'false_negatives': int(cm[1, 0]),
            'true_positives': int(cm[1, 1])
        }

        metrics['evaluated_at'] = datetime.utcnow().isoformat()

        return metrics

    def check_drift(
        self,
        train_features: pd.DataFrame,
        production_features: pd.DataFrame,
        threshold: float = 0.1
    ) -> dict:
        """
        Check for feature drift between training and production data.

        Args:
            train_features: Training features
            production_features: Production features
            threshold: Drift detection threshold

        Returns:
            Drift detection results
        """
        drift_detected = {}

        for col in train_features.columns:
            if col in production_features.columns:
                train_mean = train_features[col].mean()
                prod_mean = production_features[col].mean()

                if train_mean != 0:
                    drift = abs(prod_mean - train_mean) / abs(train_mean)
                    drift_detected[col] = {
                        'train_mean': float(train_mean),
                        'prod_mean': float(prod_mean),
                        'drift_percentage': float(drift * 100),
                        'drift_detected': drift > threshold
                    }

        return {
            'checked_at': datetime.utcnow().isoformat(),
            'features': drift_detected,
            'any_drift_detected': any(f['drift_detected'] for f in drift_detected.values())
        }

    def generate_report(self, metrics: dict, output_path: str):
        """Generate evaluation report."""
        with open(output_path, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"Evaluation report saved to {output_path}")
