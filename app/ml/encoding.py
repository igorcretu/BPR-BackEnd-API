"""
Shared encoding utilities for ML models
"""

import numpy as np
import pandas as pd


class TargetEncoder:
    """
    Target encoding with smoothing to prevent overfitting.
    Much better than LabelEncoder for brand/model with many categories.
    """
    def __init__(self, smoothing: float = 20.0):
        self.smoothing = smoothing
        self.global_mean = None
        self.encodings = {}
    
    def fit(self, X: pd.Series, y: pd.Series) -> 'TargetEncoder':
        self.global_mean = y.mean()
        
        stats = pd.DataFrame({'category': X, 'target': y})
        agg = stats.groupby('category')['target'].agg(['mean', 'count'])
        
        # Smoothed encoding
        smoothing_factor = agg['count'] / (agg['count'] + self.smoothing)
        self.encodings = (smoothing_factor * agg['mean'] + (1 - smoothing_factor) * self.global_mean).to_dict()
        
        return self
    
    def transform(self, X: pd.Series) -> np.ndarray:
        return X.map(lambda x: self.encodings.get(x, self.global_mean)).values
    
    def fit_transform(self, X: pd.Series, y: pd.Series) -> np.ndarray:
        self.fit(X, y)
        return self.transform(X)
