# Phase 4: ML Pipeline & Analytics

**Duration**: 8-10 days
**Goal**: Build production ML pipeline for engagement prediction, risk classification, and A/B testing framework

## Overview
This phase implements machine learning for adaptive learning optimization. We prioritize:
1. **Engagement Prediction** (XGBoost model predicting lesson completion likelihood)
2. **Risk Classification** (identify at-risk learners before dropout)
3. **Feature Engineering** (transform raw engagement data into ML features)
4. **Model Serving** (real-time inference via API)
5. **A/B Testing** (experiment framework for content variations)
6. **Analytics Dashboard** (Jupyter notebooks for insights)

## Prerequisites
- [ ] Phase 3 complete (Rails API collecting engagement data)
- [ ] Python 3.11+ environment
- [ ] PostgreSQL with engagement metrics data
- [ ] Basic understanding of ML concepts (classification, feature engineering)
- [ ] Optional: AWS account for SageMaker deployment

## 1. ML Development Environment

### 1.1 Create ML Service Structure
- [ ] Create directory structure
  ```bash
  mkdir -p app/ml_service/{models,features,evaluation,serving,notebooks}
  cd app/ml_service
  ```

- [ ] Create `pyproject.toml` for ML dependencies
  ```toml
  [project]
  name = "bmo-learning-ml"
  version = "0.1.0"
  requires-python = ">=3.11"
  dependencies = [
      "pandas>=2.1.0",
      "numpy>=1.26.0",
      "scikit-learn>=1.3.0",
      "xgboost>=2.0.0",
      "lightgbm>=4.1.0",
      "optuna>=3.4.0",
      "mlflow>=2.17.2",
      "fastapi>=0.121.2",
      "pydantic>=2.12.4",
      "sqlalchemy>=2.0.0",
      "psycopg2-binary>=2.9.0",
      "redis>=5.0.0",
      "jupyter>=1.0.0",
      "matplotlib>=3.8.0",
      "seaborn>=0.13.0",
      "plotly>=5.17.0",
      "shap>=0.43.0",
  ]

  [project.optional-dependencies]
  dev = [
      "pytest>=7.4.0",
      "pytest-cov>=4.1.0",
      "pytest-mock>=3.12.0",
      "black>=23.10.0",
      "ruff>=0.1.0",
      "mypy>=1.6.0",
  ]
  sagemaker = [
      "boto3>=1.28.0",
      "sagemaker>=2.189.0",
  ]
  ```

- [ ] Install dependencies
  ```bash
  uv pip install -e ".[dev]"
  ```

**Validation**: `uv pip list` shows all ML packages installed

### 1.2 Database Connection
- [ ] Create `app/ml_service/database.py`
  ```python
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  import os

  DATABASE_URL = os.getenv(
      'DATABASE_URL',
      'postgresql://postgres:postgres@localhost:5432/bmo_learning_development'
  )

  engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
  SessionLocal = sessionmaker(bind=engine)

  def get_db():
      """Get database session - use as context manager"""
      with SessionLocal() as session:
          yield session
  ```

**Validation**: Test database connection with simple query

## 2. Feature Engineering Pipeline

### 2.1 Feature Extractor
- [ ] Create `app/ml_service/features/engagement_features.py`
  ```python
  import pandas as pd
  import numpy as np
  from datetime import datetime, timedelta
  from sqlalchemy.orm import Session
  import structlog

  logger = structlog.get_logger()

  class EngagementFeatureExtractor:
      """Extract ML features from engagement metrics"""

      def __init__(self, db_session: Session):
          self.db = db_session

      def extract_learner_features(self, learner_id: int, as_of_date: datetime = None) -> dict:
          """
          Extract features for a single learner.

          Features:
          - Behavioral: completion rate, avg time, streak
          - Temporal: day of week patterns, time of day
          - Content: topic preferences, difficulty adaptation
          - Engagement: response latency, channel switches
          """
          if as_of_date is None:
              as_of_date = datetime.now()

          # Fetch raw data
          metrics = self._fetch_engagement_metrics(learner_id, as_of_date)
          assessments = self._fetch_assessment_results(learner_id, as_of_date)
          learning_paths = self._fetch_learning_paths(learner_id, as_of_date)

          features = {}

          # Behavioral features
          features.update(self._extract_behavioral_features(metrics, assessments))

          # Temporal features
          features.update(self._extract_temporal_features(metrics))

          # Content features
          features.update(self._extract_content_features(learning_paths, assessments))

          # Engagement features
          features.update(self._extract_engagement_features(metrics))

          logger.info("Features extracted", learner_id=learner_id, feature_count=len(features))
          return features

      def _fetch_engagement_metrics(self, learner_id: int, as_of_date: datetime) -> pd.DataFrame:
          """Fetch engagement metrics from database"""
          query = """
              SELECT
                  event_type,
                  event_data,
                  channel,
                  recorded_at
              FROM engagement_metrics
              WHERE learner_id = :learner_id
                AND recorded_at <= :as_of_date
              ORDER BY recorded_at DESC
              LIMIT 1000
          """
          return pd.read_sql(query, self.db.bind, params={'learner_id': learner_id, 'as_of_date': as_of_date})

      def _fetch_assessment_results(self, learner_id: int, as_of_date: datetime) -> pd.DataFrame:
          """Fetch assessment results"""
          query = """
              SELECT
                  is_correct,
                  time_taken_seconds,
                  attempted_at
              FROM assessment_results
              WHERE learner_id = :learner_id
                AND attempted_at <= :as_of_date
              ORDER BY attempted_at DESC
          """
          return pd.read_sql(query, self.db.bind, params={'learner_id': learner_id, 'as_of_date': as_of_date})

      def _fetch_learning_paths(self, learner_id: int, as_of_date: datetime) -> pd.DataFrame:
          """Fetch learning path data"""
          query = """
              SELECT
                  difficulty,
                  completion_percentage,
                  status,
                  started_at,
                  completed_at
              FROM learning_paths
              WHERE learner_id = :learner_id
                AND started_at <= :as_of_date
          """
          return pd.read_sql(query, self.db.bind, params={'learner_id': learner_id, 'as_of_date': as_of_date})

      def _extract_behavioral_features(self, metrics: pd.DataFrame, assessments: pd.DataFrame) -> dict:
          """Extract behavioral features"""
          features = {}

          if len(assessments) > 0:
              # Completion rate
              features['completion_rate'] = assessments['is_correct'].mean()

              # Average assessment time
              features['avg_assessment_time'] = assessments['time_taken_seconds'].mean()
              features['std_assessment_time'] = assessments['time_taken_seconds'].std()

              # Recent performance (last 7 days)
              recent = assessments[assessments['attempted_at'] >= (datetime.now() - timedelta(days=7))]
              features['recent_completion_rate'] = recent['is_correct'].mean() if len(recent) > 0 else 0.0

              # Streak (consecutive correct answers)
              features['current_streak'] = self._calculate_streak(assessments['is_correct'].values)
          else:
              features['completion_rate'] = 0.0
              features['avg_assessment_time'] = 0.0
              features['std_assessment_time'] = 0.0
              features['recent_completion_rate'] = 0.0
              features['current_streak'] = 0

          # Engagement frequency
          if len(metrics) > 0:
              lesson_events = metrics[metrics['event_type'] == 'lesson_started']
              features['lessons_per_week'] = len(lesson_events[
                  lesson_events['recorded_at'] >= (datetime.now() - timedelta(days=7))
              ])
          else:
              features['lessons_per_week'] = 0

          return features

      def _extract_temporal_features(self, metrics: pd.DataFrame) -> dict:
          """Extract temporal patterns"""
          features = {}

          if len(metrics) > 0:
              metrics['hour'] = pd.to_datetime(metrics['recorded_at']).dt.hour
              metrics['day_of_week'] = pd.to_datetime(metrics['recorded_at']).dt.dayofweek

              # Most active hour
              features['most_active_hour'] = metrics['hour'].mode()[0] if len(metrics) > 0 else 9

              # Weekend vs weekday engagement
              weekend_engagement = len(metrics[metrics['day_of_week'] >= 5])
              weekday_engagement = len(metrics[metrics['day_of_week'] < 5])
              features['weekend_engagement_ratio'] = (
                  weekend_engagement / (weekday_engagement + 1)  # Avoid division by zero
              )

              # Days since last engagement
              features['days_since_last_engagement'] = (
                  datetime.now() - pd.to_datetime(metrics['recorded_at'].max())
              ).days
          else:
              features['most_active_hour'] = 9
              features['weekend_engagement_ratio'] = 0.0
              features['days_since_last_engagement'] = 999

          return features

      def _extract_content_features(self, learning_paths: pd.DataFrame, assessments: pd.DataFrame) -> dict:
          """Extract content preference features"""
          features = {}

          if len(learning_paths) > 0:
              # Average completion percentage
              features['avg_path_completion'] = learning_paths['completion_percentage'].mean()

              # Number of completed paths
              features['completed_paths'] = len(learning_paths[learning_paths['status'] == 'completed'])

              # Difficulty level (encoded)
              difficulty_map = {'beginner': 0, 'intermediate': 1, 'advanced': 2}
              features['avg_difficulty'] = learning_paths['difficulty'].map(difficulty_map).mean()
          else:
              features['avg_path_completion'] = 0.0
              features['completed_paths'] = 0
              features['avg_difficulty'] = 0.0

          # Total assessments taken
          features['total_assessments'] = len(assessments)

          return features

      def _extract_engagement_features(self, metrics: pd.DataFrame) -> dict:
          """Extract engagement depth features"""
          features = {}

          if len(metrics) > 0:
              # Channel diversity (how many channels used)
              features['channel_diversity'] = metrics['channel'].nunique()

              # Most used channel (encoded)
              channel_map = {'slack': 0, 'sms': 1, 'email': 2, 'web': 3}
              features['primary_channel'] = channel_map.get(
                  metrics['channel'].mode()[0] if len(metrics) > 0 else 'web',
                  3
              )

              # Event type diversity
              features['event_type_diversity'] = metrics['event_type'].nunique()
          else:
              features['channel_diversity'] = 0
              features['primary_channel'] = 3
              features['event_type_diversity'] = 0

          return features

      def _calculate_streak(self, results: np.ndarray) -> int:
          """Calculate current streak of correct answers"""
          streak = 0
          for result in results[::-1]:  # Reverse to start from most recent
              if result:
                  streak += 1
              else:
                  break
          return streak

      def extract_batch_features(self, learner_ids: list[int], as_of_date: datetime = None) -> pd.DataFrame:
          """Extract features for multiple learners"""
          features_list = []

          for learner_id in learner_ids:
              try:
                  features = self.extract_learner_features(learner_id, as_of_date)
                  features['learner_id'] = learner_id
                  features_list.append(features)
              except Exception as e:
                  logger.error("Feature extraction failed", learner_id=learner_id, error=str(e))

          return pd.DataFrame(features_list)
  ```

**Why These Features**:
- **Behavioral**: Directly correlated with engagement (completion rate, streaks)
- **Temporal**: Identifies when learners are most active (optimize delivery time)
- **Content**: Reveals difficulty preferences (adaptive learning)
- **Engagement**: Channel preferences inform delivery strategy

### 2.2 Feature Store (Redis)
- [ ] Create `app/ml_service/features/feature_store.py`
  ```python
  import redis
  import json
  from datetime import timedelta
  import os

  class FeatureStore:
      """Cache computed features in Redis"""

      def __init__(self):
          self.redis_client = redis.from_url(
              os.getenv('REDIS_URL', 'redis://localhost:6379/1')
          )
          self.ttl = timedelta(hours=24)

      def get_features(self, learner_id: int) -> dict | None:
          """Retrieve cached features"""
          key = f"features:learner:{learner_id}"
          cached = self.redis_client.get(key)

          if cached:
              return json.loads(cached)
          return None

      def set_features(self, learner_id: int, features: dict):
          """Cache features with TTL"""
          key = f"features:learner:{learner_id}"
          self.redis_client.setex(
              key,
              self.ttl,
              json.dumps(features)
          )

      def invalidate(self, learner_id: int):
          """Invalidate cached features"""
          key = f"features:learner:{learner_id}"
          self.redis_client.delete(key)
  ```

**Validation**: Test feature extraction for sample learner

## 3. Engagement Prediction Model

### 3.1 Dataset Preparation
- [ ] Create `app/ml_service/models/dataset.py`
  ```python
  import pandas as pd
  from sklearn.model_selection import train_test_split
  from sqlalchemy.orm import Session
  import structlog

  logger = structlog.get_logger()

  class EngagementDataset:
      """Prepare training dataset for engagement prediction"""

      def __init__(self, db_session: Session):
          self.db = db_session

      def create_training_dataset(self, lookback_days: int = 30) -> pd.DataFrame:
          """
          Create labeled dataset for engagement prediction.

          Target: will_complete_next_lesson (binary classification)
          - 1: Learner completed lesson within 48 hours of receiving it
          - 0: Learner did not complete lesson
          """
          query = """
              SELECT
                  em.learner_id,
                  em.recorded_at as lesson_sent_at,
                  CASE
                      WHEN ml.completed_at IS NOT NULL
                           AND ml.completed_at <= em.recorded_at + INTERVAL '48 hours'
                      THEN 1
                      ELSE 0
                  END as will_complete_next_lesson
              FROM engagement_metrics em
              LEFT JOIN microlessons ml ON em.event_data->>'microlesson_id' = ml.id::text
              WHERE em.event_type = 'lesson_sent'
                AND em.recorded_at >= NOW() - INTERVAL :lookback_days DAY
          """

          df = pd.read_sql(query, self.db.bind, params={'lookback_days': lookback_days})
          logger.info("Training dataset created", rows=len(df), positive_class=df['will_complete_next_lesson'].sum())

          return df

      def prepare_features_and_target(self, df: pd.DataFrame, feature_extractor) -> tuple:
          """Extract features for each row and prepare X, y"""
          features_list = []

          for _, row in df.iterrows():
              features = feature_extractor.extract_learner_features(
                  learner_id=row['learner_id'],
                  as_of_date=row['lesson_sent_at']
              )
              features_list.append(features)

          X = pd.DataFrame(features_list)
          y = df['will_complete_next_lesson']

          return X, y

      def split_dataset(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2):
          """Split into train and test sets"""
          X_train, X_test, y_train, y_test = train_test_split(
              X, y, test_size=test_size, random_state=42, stratify=y
          )

          logger.info(
              "Dataset split",
              train_size=len(X_train),
              test_size=len(X_test),
              positive_rate=y_train.mean()
          )

          return X_train, X_test, y_train, y_test
  ```

### 3.2 XGBoost Model Training
- [ ] Create `app/ml_service/models/engagement_predictor.py`
  ```python
  import xgboost as xgb
  from sklearn.metrics import (
      accuracy_score, precision_score, recall_score,
      f1_score, roc_auc_score, classification_report
  )
  import pandas as pd
  import numpy as np
  import joblib
  import structlog

  logger = structlog.get_logger()

  class EngagementPredictor:
      """XGBoost model for predicting lesson completion"""

      def __init__(self, model_path: str = None):
          self.model = None
          self.feature_names = None

          if model_path:
              self.load_model(model_path)

      def train(
          self,
          X_train: pd.DataFrame,
          y_train: pd.Series,
          X_val: pd.DataFrame = None,
          y_val: pd.Series = None,
          **xgb_params
      ):
          """Train XGBoost classifier"""
          self.feature_names = X_train.columns.tolist()

          # Default params (can be overridden)
          params = {
              'objective': 'binary:logistic',
              'eval_metric': 'auc',
              'max_depth': 6,
              'learning_rate': 0.1,
              'subsample': 0.8,
              'colsample_bytree': 0.8,
              'min_child_weight': 1,
              'gamma': 0,
              'reg_alpha': 0,
              'reg_lambda': 1,
              'seed': 42,
          }
          params.update(xgb_params)

          # Prepare DMatrix
          dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=self.feature_names)

          evals = [(dtrain, 'train')]
          eval_result = {}
          if X_val is not None and y_val is not None:
              dval = xgb.DMatrix(X_val, label=y_val, feature_names=self.feature_names)
              evals.append((dval, 'val'))

          # Train
          logger.info("Training XGBoost model", params=params)

          self.model = xgb.train(
              params,
              dtrain,
              num_boost_round=500,
              evals=evals,
              early_stopping_rounds=50,
              verbose_eval=50,
              evals_result=eval_result
          )

          best_iteration = self.model.attr('best_iteration')
          logger.info("Training complete", best_iteration=best_iteration)

      def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
          """Predict completion probability"""
          if self.model is None:
              raise ValueError("Model not trained or loaded")

          dtest = xgb.DMatrix(X, feature_names=self.feature_names)
          return self.model.predict(dtest)

      def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
          """Predict binary class"""
          proba = self.predict_proba(X)
          return (proba >= threshold).astype(int)

      def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
          """Evaluate model performance"""
          y_pred = self.predict(X_test)
          y_proba = self.predict_proba(X_test)

          metrics = {
              'accuracy': accuracy_score(y_test, y_pred),
              'precision': precision_score(y_test, y_pred),
              'recall': recall_score(y_test, y_pred),
              'f1_score': f1_score(y_test, y_pred),
              'roc_auc': roc_auc_score(y_test, y_proba),
          }

          logger.info("Model evaluation", **metrics)
          print("\nClassification Report:")
          print(classification_report(y_test, y_pred))

          return metrics

      def get_feature_importance(self) -> pd.DataFrame:
          """Get feature importance scores"""
          importance = self.model.get_score(importance_type='gain')

          df = pd.DataFrame({
              'feature': list(importance.keys()),
              'importance': list(importance.values())
          }).sort_values('importance', ascending=False)

          return df

      def save_model(self, path: str):
          """Save model to disk"""
          self.model.save_model(path)
          joblib.dump(self.feature_names, f"{path}.features")
          logger.info("Model saved", path=path)

      def load_model(self, path: str):
          """Load model from disk"""
          self.model = xgb.Booster()
          self.model.load_model(path)
          self.feature_names = joblib.load(f"{path}.features")
          logger.info("Model loaded", path=path)
  ```

### 3.3 Hyperparameter Tuning with Optuna
- [ ] Create `app/ml_service/models/hyperparameter_tuning.py`
  ```python
  import optuna
  from optuna.integration import XGBoostPruningCallback
  import xgboost as xgb
  from sklearn.metrics import roc_auc_score
  import structlog

  logger = structlog.get_logger()

  class HyperparameterTuner:
      """Optimize XGBoost hyperparameters using Optuna"""

      def __init__(self, X_train, y_train, X_val, y_val):
          self.X_train = X_train
          self.y_train = y_train
          self.X_val = X_val
          self.y_val = y_val

      def objective(self, trial: optuna.Trial) -> float:
          """Optuna objective function"""
          params = {
              'objective': 'binary:logistic',
              'eval_metric': 'auc',
              'max_depth': trial.suggest_int('max_depth', 3, 10),
              'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
              'subsample': trial.suggest_float('subsample', 0.6, 1.0),
              'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
              'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
              'gamma': trial.suggest_float('gamma', 0, 5),
              'reg_alpha': trial.suggest_float('reg_alpha', 0, 5),
              'reg_lambda': trial.suggest_float('reg_lambda', 0, 5),
              'seed': 42,
          }

          dtrain = xgb.DMatrix(self.X_train, label=self.y_train)
          dval = xgb.DMatrix(self.X_val, label=self.y_val)

          pruning_callback = XGBoostPruningCallback(trial, 'val-auc')

          model = xgb.train(
              params,
              dtrain,
              num_boost_round=1000,
              evals=[(dval, 'val')],
              early_stopping_rounds=50,
              verbose_eval=False,
              callbacks=[pruning_callback]
          )

          y_pred = model.predict(dval)
          auc = roc_auc_score(self.y_val, y_pred)

          return auc

      def optimize(self, n_trials: int = 50) -> dict:
          """Run hyperparameter optimization"""
          study = optuna.create_study(direction='maximize')
          study.optimize(self.objective, n_trials=n_trials, show_progress_bar=True)

          logger.info(
              "Optimization complete",
              best_auc=study.best_value,
              best_params=study.best_params
          )

          return study.best_params
  ```

### 3.4 Training Script
- [ ] Create `app/ml_service/scripts/train_engagement_model.py`
  ```python
  #!/usr/bin/env python
  """Train engagement prediction model"""

  from app.ml_service.database import SessionLocal
  from app.ml_service.features.engagement_features import EngagementFeatureExtractor
  from app.ml_service.models.dataset import EngagementDataset
  from app.ml_service.models.engagement_predictor import EngagementPredictor
  from app.ml_service.models.hyperparameter_tuning import HyperparameterTuner
  import mlflow
  import structlog

  logger = structlog.get_logger()

  def main():
      # Initialize MLflow
      mlflow.set_tracking_uri("sqlite:///mlflow.db")  # or remote server
      mlflow.set_experiment("engagement_prediction")

      with mlflow.start_run():
          # Create dataset
          db = SessionLocal()
          dataset = EngagementDataset(db)
          feature_extractor = EngagementFeatureExtractor(db)

          logger.info("Creating training dataset...")
          df = dataset.create_training_dataset(lookback_days=60)

          logger.info("Extracting features...")
          X, y = dataset.prepare_features_and_target(df, feature_extractor)

          # Split data
          X_train, X_test, y_train, y_test = dataset.split_dataset(X, y, test_size=0.2)
          X_train, X_val, y_train, y_val = dataset.split_dataset(X_train, y_train, test_size=0.2)

          # Hyperparameter tuning (optional)
          # tuner = HyperparameterTuner(X_train, y_train, X_val, y_val)
          # best_params = tuner.optimize(n_trials=30)

          # Train model with default or tuned params
          model = EngagementPredictor()
          model.train(X_train, y_train, X_val, y_val)

          # Evaluate
          metrics = model.evaluate(X_test, y_test)

          # Log metrics to MLflow
          mlflow.log_metrics(metrics)

          # Feature importance
          importance = model.get_feature_importance()
          logger.info("Top 10 features", features=importance.head(10).to_dict())

          # Save model
          model_path = "models/engagement_predictor.xgb"
          model.save_model(model_path)
          mlflow.log_artifact(model_path)

          logger.info("Training complete", model_path=model_path)

  if __name__ == "__main__":
      main()
  ```

**Validation**: `python scripts/train_engagement_model.py` trains model with >0.70 AUC

## 4. Risk Classification Model

### 4.1 Risk Scorer
- [ ] Create `app/ml_service/models/risk_classifier.py`
  ```python
  from sklearn.ensemble import RandomForestClassifier
  from sklearn.metrics import classification_report
  import pandas as pd
  import joblib
  import structlog

  logger = structlog.get_logger()

  class RiskClassifier:
      """
      Classify learners by dropout risk.

      Risk Levels:
      - Low: Active, completing lessons regularly
      - Medium: Slowing engagement, may need intervention
      - High: Inactive >7 days, likely to drop out
      """

      def __init__(self):
          self.model = None
          self.feature_names = None

      def create_risk_labels(self, df: pd.DataFrame) -> pd.Series:
          """
          Create risk labels from engagement data.

          High Risk: days_since_last_engagement > 7 AND completion_rate < 0.5
          Medium Risk: days_since_last_engagement > 3 OR completion_rate < 0.7
          Low Risk: Otherwise
          """
          def assign_risk(row):
              if row['days_since_last_engagement'] > 7 and row['completion_rate'] < 0.5:
                  return 2  # High risk
              elif row['days_since_last_engagement'] > 3 or row['completion_rate'] < 0.7:
                  return 1  # Medium risk
              else:
                  return 0  # Low risk

          return df.apply(assign_risk, axis=1)

      def train(self, X_train: pd.DataFrame, y_train: pd.Series):
          """Train Random Forest classifier"""
          self.feature_names = X_train.columns.tolist()

          self.model = RandomForestClassifier(
              n_estimators=200,
              max_depth=10,
              min_samples_split=10,
              class_weight='balanced',
              random_state=42
          )

          logger.info("Training risk classifier...")
          self.model.fit(X_train, y_train)
          logger.info("Training complete")

      def predict(self, X: pd.DataFrame) -> pd.Series:
          """Predict risk level"""
          return self.model.predict(X)

      def predict_proba(self, X: pd.DataFrame) -> pd.DataFrame:
          """Predict risk probabilities"""
          proba = self.model.predict_proba(X)
          return pd.DataFrame(proba, columns=['low_risk', 'medium_risk', 'high_risk'])

      def evaluate(self, X_test: pd.DataFrame, y_test: pd.Series):
          """Evaluate classifier"""
          y_pred = self.predict(X_test)

          print("\nRisk Classification Report:")
          print(classification_report(
              y_test, y_pred,
              target_names=['Low Risk', 'Medium Risk', 'High Risk']
          ))

      def save_model(self, path: str):
          """Save model"""
          joblib.dump({'model': self.model, 'features': self.feature_names}, path)
          logger.info("Risk classifier saved", path=path)

      def load_model(self, path: str):
          """Load model"""
          data = joblib.load(path)
          self.model = data['model']
          self.feature_names = data['features']
          logger.info("Risk classifier loaded", path=path)
  ```

**Validation**: Train risk classifier and evaluate performance

## 5. Model Serving API

### 5.1 Inference Endpoint
- [ ] Create `app/ml_service/serving/api.py`
  ```python
  from fastapi import FastAPI, HTTPException
  from pydantic import BaseModel
  import pandas as pd
  from app.ml_service.models.engagement_predictor import EngagementPredictor
  from app.ml_service.models.risk_classifier import RiskClassifier
  from app.ml_service.features.engagement_features import EngagementFeatureExtractor
  from app.ml_service.features.feature_store import FeatureStore
  from app.ml_service.database import SessionLocal
  import structlog

  logger = structlog.get_logger()

  app = FastAPI(title="BMO Learning ML Service", version="0.1.0")

  # Load models on startup
  engagement_model = EngagementPredictor(model_path="models/engagement_predictor.xgb")
  risk_model = RiskClassifier()
  risk_model.load_model("models/risk_classifier.pkl")

  feature_store = FeatureStore()

  class PredictionRequest(BaseModel):
      learner_id: int
      use_cache: bool = True

  class EngagementPredictionResponse(BaseModel):
      learner_id: int
      completion_probability: float
      will_complete: bool
      risk_level: str
      risk_probabilities: dict

  @app.post("/predict/engagement", response_model=EngagementPredictionResponse)
  async def predict_engagement(request: PredictionRequest):
      """Predict lesson completion likelihood and risk level"""
      try:
          # Get features (from cache or compute)
          features = None
          if request.use_cache:
              features = feature_store.get_features(request.learner_id)

          if features is None:
              db = SessionLocal()
              extractor = EngagementFeatureExtractor(db)
              features = extractor.extract_learner_features(request.learner_id)
              feature_store.set_features(request.learner_id, features)

          # Convert to DataFrame
          X = pd.DataFrame([features])

          # Engagement prediction
          completion_prob = float(engagement_model.predict_proba(X)[0])
          will_complete = completion_prob >= 0.5

          # Risk prediction
          risk_pred = risk_model.predict(X)[0]
          risk_proba = risk_model.predict_proba(X).iloc[0].to_dict()

          risk_levels = ['low', 'medium', 'high']

          return EngagementPredictionResponse(
              learner_id=request.learner_id,
              completion_probability=completion_prob,
              will_complete=will_complete,
              risk_level=risk_levels[risk_pred],
              risk_probabilities=risk_proba
          )

      except Exception as e:
          logger.error("Prediction failed", learner_id=request.learner_id, error=str(e))
          raise HTTPException(status_code=500, detail=str(e))

  @app.get("/health")
  async def health_check():
      return {"status": "healthy", "models_loaded": True}

  @app.post("/features/invalidate/{learner_id}")
  async def invalidate_features(learner_id: int):
      """Invalidate cached features for a learner"""
      feature_store.invalidate(learner_id)
      return {"status": "invalidated", "learner_id": learner_id}
  ```

**Validation**: `uvicorn app.ml_service.serving.api:app --reload` starts successfully

## 6. A/B Testing Framework

### 6.1 Experiment Manager
- [ ] Create `app/ml_service/experiments/ab_test.py`
  ```python
  import hashlib
  from enum import Enum
  from dataclasses import dataclass
  from datetime import datetime
  import structlog

  logger = structlog.get_logger()

  class VariantType(str, Enum):
      CONTROL = "control"
      TREATMENT_A = "treatment_a"
      TREATMENT_B = "treatment_b"

  @dataclass
  class Experiment:
      name: str
      start_date: datetime
      end_date: datetime
      traffic_allocation: dict[VariantType, float]  # e.g., {CONTROL: 0.5, TREATMENT_A: 0.5}

  class ABTestManager:
      """Manage A/B tests for content and delivery strategies"""

      def __init__(self):
          self.experiments = {}

      def create_experiment(
          self,
          name: str,
          start_date: datetime,
          end_date: datetime,
          traffic_allocation: dict[VariantType, float]
      ):
          """Create new A/B test experiment"""
          # Validate allocation sums to 1.0
          if sum(traffic_allocation.values()) != 1.0:
              raise ValueError("Traffic allocation must sum to 1.0")

          experiment = Experiment(
              name=name,
              start_date=start_date,
              end_date=end_date,
              traffic_allocation=traffic_allocation
          )

          self.experiments[name] = experiment
          logger.info("Experiment created", name=name, allocation=traffic_allocation)

      def assign_variant(self, experiment_name: str, learner_id: int) -> VariantType:
          """
          Consistently assign learner to a variant using hashing.

          Uses consistent hashing to ensure:
          - Same learner always gets same variant
          - Distribution matches traffic allocation
          """
          experiment = self.experiments.get(experiment_name)
          if not experiment:
              raise ValueError(f"Experiment {experiment_name} not found")

          # Check if experiment is active
          now = datetime.now()
          if not (experiment.start_date <= now <= experiment.end_date):
              logger.warning("Experiment not active", experiment=experiment_name)
              return VariantType.CONTROL

          # Consistent hashing
          hash_input = f"{experiment_name}:{learner_id}".encode()
          hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
          bucket = (hash_value % 100) / 100.0  # 0.00 to 0.99

          # Assign variant based on traffic allocation
          cumulative = 0.0
          for variant, allocation in experiment.traffic_allocation.items():
              cumulative += allocation
              if bucket < cumulative:
                  logger.info(
                      "Variant assigned",
                      experiment=experiment_name,
                      learner_id=learner_id,
                      variant=variant
                  )
                  return variant

          return VariantType.CONTROL

  # Example usage
  ab_manager = ABTestManager()

  # Experiment: Short vs Long lesson content
  ab_manager.create_experiment(
      name="lesson_length_v1",
      start_date=datetime(2025, 1, 1),
      end_date=datetime(2025, 2, 1),
      traffic_allocation={
          VariantType.CONTROL: 0.5,      # Current length (500 tokens)
          VariantType.TREATMENT_A: 0.5,  # Shorter (300 tokens)
      }
  )
  ```

### 6.2 Experiment Tracking
- [ ] Create Rails migration for experiment tracking
  ```ruby
  # In Rails API
  rails generate model ExperimentAssignment \
    learner_id:references \
    experiment_name:string \
    variant:string \
    assigned_at:datetime
  ```

**Validation**: Test variant assignment is consistent

## 7. Analytics Dashboard

### 7.1 Jupyter Notebook Setup
- [ ] Create `app/ml_service/notebooks/engagement_analysis.ipynb`
  ```python
  # Cell 1: Imports
  import pandas as pd
  import matplotlib.pyplot as plt
  import seaborn as sns
  from sqlalchemy import create_engine
  import plotly.express as px

  # Cell 2: Database connection
  engine = create_engine('postgresql://postgres:postgres@localhost:5432/bmo_learning_development')

  # Cell 3: Load engagement data
  query = """
      SELECT
          l.role,
          l.knowledge_level,
          l.preferred_channel,
          COUNT(DISTINCT em.id) as total_events,
          COUNT(DISTINCT CASE WHEN em.event_type = 'lesson_completed' THEN em.id END) as lessons_completed,
          AVG(ar.is_correct::int) * 100 as avg_score
      FROM learners l
      LEFT JOIN engagement_metrics em ON l.id = em.learner_id
      LEFT JOIN assessment_results ar ON l.id = ar.learner_id
      GROUP BY l.role, l.knowledge_level, l.preferred_channel
  """

  df = pd.read_sql(query, engine)

  # Cell 4: Visualization - Completion rate by role
  fig = px.bar(
      df,
      x='role',
      y='lessons_completed',
      color='preferred_channel',
      title='Lesson Completions by Role and Channel'
  )
  fig.show()

  # Cell 5: Engagement heatmap
  pivot = df.pivot_table(
      values='avg_score',
      index='role',
      columns='knowledge_level',
      aggfunc='mean'
  )

  plt.figure(figsize=(10, 6))
  sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlGnBu')
  plt.title('Average Score by Role and Knowledge Level')
  plt.show()
  ```

**Validation**: Run notebook and verify visualizations

## 8. Optional: SageMaker Deployment

### 8.1 SageMaker Training Script
- [ ] Create `app/ml_service/sagemaker/train.py`
  ```python
  """SageMaker training script"""
  import argparse
  import os
  import xgboost as xgb
  import pandas as pd
  from sklearn.metrics import roc_auc_score

  def main():
      parser = argparse.ArgumentParser()
      parser.add_argument('--max-depth', type=int, default=6)
      parser.add_argument('--learning-rate', type=float, default=0.1)
      parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR'))
      parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN'))
      parser.add_argument('--validation', type=str, default=os.environ.get('SM_CHANNEL_VALIDATION'))

      args = parser.parse_args()

      # Load data
      train_df = pd.read_csv(f"{args.train}/train.csv")
      val_df = pd.read_csv(f"{args.validation}/validation.csv")

      X_train = train_df.drop('target', axis=1)
      y_train = train_df['target']
      X_val = val_df.drop('target', axis=1)
      y_val = val_df['target']

      # Train
      dtrain = xgb.DMatrix(X_train, label=y_train)
      dval = xgb.DMatrix(X_val, label=y_val)

      params = {
          'objective': 'binary:logistic',
          'max_depth': args.max_depth,
          'learning_rate': args.learning_rate,
      }

      model = xgb.train(
          params,
          dtrain,
          num_boost_round=100,
          evals=[(dval, 'val')],
          early_stopping_rounds=10
      )

      # Evaluate
      y_pred = model.predict(dval)
      auc = roc_auc_score(y_val, y_pred)
      print(f"Validation AUC: {auc:.4f}")

      # Save model
      model.save_model(f"{args.model_dir}/model.xgb")

  if __name__ == "__main__":
      main()
  ```

**Validation**: Test locally before deploying to SageMaker

## Phase 4 Checklist Summary

### Feature Engineering
- [ ] Engagement feature extractor with 15+ features
- [ ] Behavioral, temporal, content, engagement features
- [ ] Feature store with Redis caching
- [ ] Batch feature extraction

### Models
- [ ] XGBoost engagement predictor (AUC >0.70)
- [ ] Random Forest risk classifier (3 classes)
- [ ] Hyperparameter tuning with Optuna
- [ ] Model training scripts
- [ ] MLflow experiment tracking

### Model Serving
- [ ] FastAPI inference endpoint
- [ ] Feature caching
- [ ] Prediction API with risk scoring
- [ ] Health check endpoint

### A/B Testing
- [ ] Experiment manager with consistent hashing
- [ ] Variant assignment
- [ ] Experiment tracking in Rails
- [ ] Traffic allocation

### Analytics
- [ ] Jupyter notebook dashboard
- [ ] Engagement visualizations
- [ ] Performance metrics
- [ ] Feature importance analysis

### Testing
- [ ] Unit tests for feature extractor
- [ ] Model evaluation tests
- [ ] API endpoint tests
- [ ] A/B test assignment tests

### Optional
- [ ] SageMaker training script
- [ ] SageMaker endpoint deployment
- [ ] Model monitoring

## Handoff Criteria
- [ ] Engagement model achieves AUC >0.70 on test set
- [ ] Risk classifier accuracy >0.75
- [ ] Feature extraction completes in <5 seconds per learner
- [ ] Inference API responds in <200ms
- [ ] A/B test variant assignment is consistent
- [ ] Jupyter notebooks run without errors
- [ ] All tests pass with >80% coverage

## Next Phase
Proceed to **[Phase 5: Infrastructure & Deployment](./05-infrastructure.md)** to deploy to AWS.

---

**Estimated Time**: 8-10 days
**Complexity**: High
**Key Learning**: XGBoost, Feature Engineering, Model Serving, A/B Testing
**Dependencies**: Phase 3 (Rails API with engagement data)
