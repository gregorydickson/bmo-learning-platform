"""Engagement prediction model using XGBoost."""
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import joblib
from pathlib import Path
import json


class EngagementPredictor:
    """Predicts learner engagement for optimal lesson timing."""

    def __init__(self, model_path: str | None = None):
        """
        Initialize engagement predictor.

        Args:
            model_path: Path to saved model (optional)
        """
        if model_path and Path(model_path).exists():
            self.model = joblib.load(model_path)
        else:
            self.model = XGBClassifier(
                max_depth=5,
                learning_rate=0.1,
                n_estimators=100,
                objective='binary:logistic',
                random_state=42
            )

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for training/prediction.

        Args:
            df: Input dataframe

        Returns:
            Feature dataframe
        """
        features = pd.DataFrame()

        # Time-based features
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            features['hour_of_day'] = df['timestamp'].dt.hour
            features['day_of_week'] = df['timestamp'].dt.dayofweek
            features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)

        # Historical engagement
        if 'completion_rate' in df.columns:
            features['completion_rate'] = df['completion_rate']

        if 'quiz_accuracy' in df.columns:
            features['quiz_accuracy'] = df['quiz_accuracy']

        # Response time features
        if 'avg_response_time' in df.columns:
            features['avg_response_time'] = df['avg_response_time']

        # Lesson count
        if 'lessons_completed' in df.columns:
            features['lessons_completed'] = df['lessons_completed']

        return features

    def train(self, X: pd.DataFrame, y: pd.Series) -> dict:
        """
        Train the engagement prediction model.

        Args:
            X: Feature dataframe
            y: Target variable (1=engaged, 0=not engaged)

        Returns:
            Training metrics
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        # Train model
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        # Evaluate
        y_pred = self.model.predict(X_test)
        y_pred_proba = self.model.predict_proba(X_test)[:, 1]

        metrics = {
            'accuracy': (y_pred == y_test).mean(),
            'roc_auc': roc_auc_score(y_test, y_pred_proba),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }

        return metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict engagement probability.

        Args:
            X: Feature dataframe

        Returns:
            Engagement probabilities
        """
        return self.model.predict_proba(X)[:, 1]

    def find_optimal_time(
        self,
        learner_features: dict,
        start_hour: int = 9,
        end_hour: int = 18
    ) -> dict:
        """
        Find optimal time for lesson delivery.

        Args:
            learner_features: Learner characteristics
            start_hour: Start of time window
            end_hour: End of time window

        Returns:
            Optimal time and confidence
        """
        # Generate features for each hour
        hours = range(start_hour, end_hour + 1)
        predictions = []

        for hour in hours:
            features = pd.DataFrame([{
                'hour_of_day': hour,
                'day_of_week': learner_features.get('day_of_week', 2),
                'is_weekend': 0,
                'completion_rate': learner_features.get('completion_rate', 0.7),
                'quiz_accuracy': learner_features.get('quiz_accuracy', 0.8),
                'avg_response_time': learner_features.get('avg_response_time', 300),
                'lessons_completed': learner_features.get('lessons_completed', 5)
            }])

            prob = self.predict(features)[0]
            predictions.append({'hour': hour, 'probability': float(prob)})

        # Find best time
        best = max(predictions, key=lambda x: x['probability'])

        return {
            'optimal_hour': best['hour'],
            'confidence': best['probability'],
            'all_predictions': predictions
        }

    def save(self, path: str):
        """Save model to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, path)

        # Save feature importance
        importance = pd.DataFrame({
            'feature': self.model.get_booster().feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        importance.to_csv(f"{path}.importance.csv", index=False)


def train_engagement_model():
    """Train and save engagement prediction model."""
    # Generate synthetic training data
    np.random.seed(42)
    n_samples = 1000

    # Simulate features
    data = {
        'hour_of_day': np.random.randint(0, 24, n_samples),
        'day_of_week': np.random.randint(0, 7, n_samples),
        'is_weekend': np.random.randint(0, 2, n_samples),
        'completion_rate': np.random.uniform(0, 1, n_samples),
        'quiz_accuracy': np.random.uniform(0, 1, n_samples),
        'avg_response_time': np.random.uniform(60, 600, n_samples),
        'lessons_completed': np.random.randint(0, 50, n_samples)
    }

    X = pd.DataFrame(data)

    # Simulate target: higher engagement during business hours
    engagement_prob = (
        (X['hour_of_day'] >= 9) & (X['hour_of_day'] <= 17) &
        (X['is_weekend'] == 0) &
        (X['completion_rate'] > 0.5)
    ).astype(float) * 0.8 + np.random.uniform(0, 0.2, n_samples)

    y = (engagement_prob > 0.6).astype(int)

    # Train model
    predictor = EngagementPredictor()
    metrics = predictor.train(X, y)

    print("Training Metrics:")
    print(json.dumps(metrics, indent=2, default=str))

    # Save model
    model_path = "ml_pipeline/models/engagement_predictor/model.pkl"
    predictor.save(model_path)
    print(f"\nModel saved to {model_path}")

    return predictor


if __name__ == "__main__":
    train_engagement_model()
