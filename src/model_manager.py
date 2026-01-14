from typing import Any, List, Dict, Tuple, Optional, Literal

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error
)
from xgboost import XGBClassifier, XGBRegressor

import matplotlib.pyplot as plt

from src.pipeline_manager import PreprocessorManager 


class InvalidModelError(Exception):
    pass


class ModelManager:
    def __init__(
        self,
        datasets: Optional[Dict[str, Any]] = None,
        columns: Optional[Dict[str, List[str]]] = None,
        model_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        model_type: Literal["classification", "regression"] = "classification",
        scale_numeric: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        columns = columns or {}
        model_metadata = model_metadata or {}

        self.features = columns.get("features") or columns.get("all", [])
        self.numerical_features = columns.get("numerical_features") or columns.get("numeric", [])
        self.categorical_features = columns.get("categorical_features") or columns.get("categorical", [])
        self.target_field = columns.get("target", [])
        self.metadata_cols = columns.get("metadata", [])

        if not self.target_field:
            raise ValueError("columns['target'] must contain the target column name")

        self.hyperparameters = model_metadata.get("hyperparameters", {}) or {}
        self.model_type = model_type
        self.scale_numeric = scale_numeric
        self.inner_model: Optional[XGBClassifier | XGBRegressor] = None
        self.preprocessor = None
        self.metrics = []

    def _get_feature_columns(self) -> List[str]:
        exclude_cols = set(self.target_field + self.metadata_cols)
        if self.features:
            return [f for f in self.features if f not in exclude_cols]
        return self.numerical_features + self.categorical_features

    def _create_preprocessor(self):
        return PreprocessorManager(
            numerical_features=self.numerical_features,
            categorical_features=self.categorical_features,
            scale_numeric=self.scale_numeric,
        ).build()

    def train_model(self, train_set: pd.DataFrame, test_set: pd.DataFrame = None) -> None:
        target_col = self.target_field[0]
        feature_cols = self._get_feature_columns()

        X_train = train_set[feature_cols].copy()
        
        if self.model_type == "classification":
            y_train = train_set[target_col].astype(int).copy()
        else:
            y_train = train_set[target_col].copy()

        self.preprocessor = self._create_preprocessor()
        X_train_proc = self.preprocessor.fit_transform(X_train)

        params = dict(self.hyperparameters)
        
        if self.model_type == "classification":
            self.inner_model = XGBClassifier(**params)
        else:
            self.inner_model = XGBRegressor(**params)
            
        self.inner_model.fit(X_train_proc, y_train)

    def predict(self, dataset: pd.DataFrame) -> pd.DataFrame:
        if self.inner_model is None or self.preprocessor is None:
            raise InvalidModelError("Model has not been trained yet")

        feature_cols = self._get_feature_columns()
        X = dataset[feature_cols] if all(c in dataset.columns for c in feature_cols) else dataset
        X_proc = self.preprocessor.transform(X)

        if self.model_type == "classification":
            proba = self.inner_model.predict_proba(X_proc)[:, 1]
            return pd.DataFrame({"score": np.asarray(proba).reshape(-1)}, index=dataset.index)
        else:
            predictions = self.inner_model.predict(X_proc)
            return pd.DataFrame({"prediction": np.asarray(predictions).reshape(-1)}, index=dataset.index)

    def evaluate_model(
        self, train_set: pd.DataFrame, test_set: pd.DataFrame, oot_set: pd.DataFrame = None
    ) -> Tuple[Dict[str, pd.DataFrame], List[Dict[str, float]]]:
        datasets = (("train", train_set), ("test", test_set), ("oot", oot_set))
        metrics = []
        artifacts = {}
        target_col = self.target_field[0]

        for name, df in datasets:
            if df is None:
                continue
            df2 = df.copy().reset_index(drop=True)
            
            if self.model_type == "classification":
                y = df2[target_col].astype(int).to_numpy()
                p = self.predict(df2)["score"].to_numpy()
                y_pred = (p >= 0.5).astype(int)
                df2["score"] = p

                metrics.append({"name": "roc_auc", "value": float(roc_auc_score(y, p)), "dataset": name})
                metrics.append({"name": "accuracy", "value": float(accuracy_score(y, y_pred)), "dataset": name})
                metrics.append({"name": "f1_score", "value": float(f1_score(y, y_pred)), "dataset": name})
            else:
                y = df2[target_col].to_numpy()
                p = self.predict(df2)["prediction"].to_numpy()
                df2["prediction"] = p

                metrics.append({"name": "rmse", "value": float(np.sqrt(mean_squared_error(y, p))), "dataset": name})
                metrics.append({"name": "mae", "value": float(mean_absolute_error(y, p)), "dataset": name})
                metrics.append({"name": "r2_score", "value": float(r2_score(y, p)), "dataset": name})
                metrics.append({"name": "mape", "value": float(mean_absolute_percentage_error(y, p)), "dataset": name})
            
            artifacts[f"scored_{name}_set"] = df2

        self.metrics = metrics
        return artifacts, metrics
    
    def get_feature_importance(self, top_n: int = 20) -> pd.DataFrame:
        """
        Retorna el feature importance del modelo entrenado.
        
        Args:
            top_n: Número de features más importantes a retornar (default: 20)
        
        Returns:
            DataFrame con features y sus importancias ordenadas descendentemente
        """
        if self.inner_model is None or self.preprocessor is None:
            raise InvalidModelError("Model has not been trained yet")
        
        # Obtener nombres de features después del preprocesamiento
        feature_names = self.preprocessor.get_feature_names_out()
        
        # Obtener importancias del modelo
        importances = self.inner_model.feature_importances_
        
        # Crear DataFrame y ordenar
        importance_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values('importance', ascending=False).reset_index(drop=True)
        
        # Retornar top N
        return importance_df.head(top_n)
    
    def plot_feature_importance(self, top_n: int = 20, figsize: Tuple[int, int] = (10, 8)):
        """
        Genera un gráfico de barras con las features más importantes.
        
        Args:
            top_n: Número de features más importantes a mostrar (default: 20)
            figsize: Tamaño de la figura (default: (10, 8))
        
        Returns:
            matplotlib figure object
        """
        importance_df = self.get_feature_importance(top_n=top_n)
        
        fig, ax = plt.subplots(figsize=figsize)
        ax.barh(importance_df['feature'][::-1], importance_df['importance'][::-1])
        ax.set_xlabel('Importance', fontsize=12)
        ax.set_ylabel('Feature', fontsize=12)
        ax.set_title(f'Top {top_n} Feature Importances', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        plt.tight_layout()
        
        return fig