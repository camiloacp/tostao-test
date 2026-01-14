from typing import Any, List, Dict, Tuple, Optional, Union
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

class InvalidModelError(Exception):
    """Exception raised for errors in loading the model.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message: str = "There was a problem loading the model"):
        """
        Args:
            message (str): Explanation of the error.
        """
        self.message = message
        super().__init__(self.message)


class PreprocessorManager:
    """
    PreprocessorManager responsible for building the sklearn ColumnTransformer used to preprocess
    numerical and categorical features.

    Extracted from ModelManager._create_preprocessor to keep concerns separated.
    """

    def __init__(
        self,
        numerical_features: List[str],
        categorical_features: List[str],
        numeric_fill_value: Union[int, float] = -1,
        categorical_fill_value: str = "missing",
        ohe_drop: Union[str, None] = "if_binary",
        ohe_sparse_output: bool = False,
        ohe_handle_unknown: str = "ignore",
        remainder: str = "drop",
        verbose_feature_names_out: bool = False,
        output_transform: str = "pandas",
        scale_numeric: bool = False,
    ) -> None:
        self.numerical_features = numerical_features or []
        self.categorical_features = categorical_features or []
        self.numeric_fill_value = numeric_fill_value
        self.categorical_fill_value = categorical_fill_value
        self.ohe_drop = ohe_drop
        self.ohe_sparse_output = ohe_sparse_output
        self.ohe_handle_unknown = ohe_handle_unknown
        self.remainder = remainder
        self.verbose_feature_names_out = verbose_feature_names_out
        self.output_transform = output_transform
        self.scale_numeric = scale_numeric

    def build(self) -> ColumnTransformer:
        """Build the preprocessing pipeline for numerical and categorical features."""
        numeric_steps = [
            ("imputer", SimpleImputer(strategy="constant", fill_value=self.numeric_fill_value)),
        ]
        
        if self.scale_numeric:
            numeric_steps.append(("scaler", StandardScaler()))
        
        numeric_transformer = Pipeline(steps=numeric_steps)

        categorical_transformer = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="constant", fill_value=self.categorical_fill_value)),
                (
                    "encoder",
                    OneHotEncoder(
                        drop=self.ohe_drop,
                        sparse_output=self.ohe_sparse_output,
                        handle_unknown=self.ohe_handle_unknown,
                    ),
                ),
            ]
        )

        preprocessor = ColumnTransformer(
            transformers=[
                ("num", numeric_transformer, self.numerical_features),
                ("cat", categorical_transformer, self.categorical_features),
            ],
            remainder=self.remainder,
            verbose_feature_names_out=self.verbose_feature_names_out,
        )

        preprocessor = preprocessor.set_output(transform=self.output_transform)
        return preprocessor