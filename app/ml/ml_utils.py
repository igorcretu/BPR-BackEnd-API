"""
ML utilities for model loading and preprocessing
Contains classes needed for deserializing trained models
"""

import os
import numpy as np
import pandas as pd

# ============================================================================
# TARGET ENCODER (for high-cardinality categoricals)
# ============================================================================

class TargetEncoder:
    """
    Target encoding with smoothing to prevent overfitting.
    Used for brand/model encoding during training.
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


# ============================================================================
# PYTORCH MODEL DEFINITIONS
# ============================================================================

try:
    import torch
    import torch.nn as nn
    
    TORCH_AVAILABLE = True
    
    class ImprovedLSTMNetwork(nn.Module):
        """Improved LSTM with residual connections and layer normalization"""
        
        def __init__(self, input_dim, hidden_dim=128, num_layers=2, dropout=0.3):
            super(ImprovedLSTMNetwork, self).__init__()
            
            # Input projection
            self.input_proj = nn.Linear(input_dim, hidden_dim)
            self.input_norm = nn.LayerNorm(hidden_dim)
            
            # LSTM layers
            self.lstm = nn.LSTM(
                hidden_dim, hidden_dim, num_layers,
                batch_first=True, dropout=dropout if num_layers > 1 else 0,
                bidirectional=False
            )
            
            # Output layers with residual
            self.dropout = nn.Dropout(dropout)
            self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
            self.fc1_norm = nn.LayerNorm(hidden_dim // 2)
            self.fc2 = nn.Linear(hidden_dim // 2, 1)
            
            self.relu = nn.ReLU()
            
        def forward(self, x):
            # Project input
            x = self.input_proj(x)
            x = self.input_norm(x)
            x = self.relu(x)
            
            # Add sequence dimension if needed
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            # LSTM
            lstm_out, _ = self.lstm(x)
            out = lstm_out[:, -1, :]  # Take last output
            
            # Output layers
            out = self.dropout(out)
            out = self.fc1(out)
            out = self.fc1_norm(out)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc2(out)
            
            return out.squeeze()

    class ImprovedGRUNetwork(nn.Module):
        """Improved GRU with layer normalization"""
        
        def __init__(self, input_dim, hidden_dim=128, num_layers=2, dropout=0.3):
            super(ImprovedGRUNetwork, self).__init__()
            
            # Input projection
            self.input_proj = nn.Linear(input_dim, hidden_dim)
            self.input_norm = nn.LayerNorm(hidden_dim)
            
            # GRU layers
            self.gru = nn.GRU(
                hidden_dim, hidden_dim, num_layers,
                batch_first=True, dropout=dropout if num_layers > 1 else 0
            )
            
            # Output layers
            self.dropout = nn.Dropout(dropout)
            self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
            self.fc1_norm = nn.LayerNorm(hidden_dim // 2)
            self.fc2 = nn.Linear(hidden_dim // 2, 1)
            
            self.relu = nn.ReLU()
            
        def forward(self, x):
            x = self.input_proj(x)
            x = self.input_norm(x)
            x = self.relu(x)
            
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            gru_out, _ = self.gru(x)
            out = gru_out[:, -1, :]
            
            out = self.dropout(out)
            out = self.fc1(out)
            out = self.fc1_norm(out)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc2(out)
            
            return out.squeeze()

except ImportError:
    TORCH_AVAILABLE = False
    ImprovedLSTMNetwork = None
    ImprovedGRUNetwork = None


def load_pytorch_model(model_path, model_type='GRU'):
    """
    Load a PyTorch model from file
    
    Args:
        model_path: Path to the .pt file
        model_type: 'LSTM' or 'GRU'
    
    Returns:
        Tuple of (model, model_info_dict)
    """
    if not TORCH_AVAILABLE:
        raise ImportError("PyTorch is not available")
    
    # Load checkpoint (weights_only=False for backward compatibility with numpy)
    checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
    
    # Extract model parameters
    input_dim = checkpoint['input_dim']
    params = checkpoint['params']
    
    # Create model
    if model_type.upper() == 'LSTM':
        model = ImprovedLSTMNetwork(
            input_dim=input_dim,
            hidden_dim=params.get('hidden_dim', 128),
            num_layers=params.get('num_layers', 2),
            dropout=params.get('dropout', 0.3)
        )
    elif model_type.upper() == 'GRU':
        model = ImprovedGRUNetwork(
            input_dim=input_dim,
            hidden_dim=params.get('hidden_dim', 128),
            num_layers=params.get('num_layers', 2),
            dropout=params.get('dropout', 0.3)
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    # Load weights
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    # Return model and normalization parameters
    model_info = {
        'y_mean': checkpoint['y_mean'],
        'y_std': checkpoint['y_std'],
        'params': params,
        'input_dim': input_dim
    }
    
    return model, model_info


def load_preprocessing_for_pytorch(model_path):
    """
    Load preprocessing objects that should be saved alongside PyTorch models.
    Looks for a companion .pkl file with the same base name.
    
    Args:
        model_path: Path to the .pt file
    
    Returns:
        Dict with scaler, feature_names, etc. or None if not found
    """
    import joblib
    
    # Look for companion preprocessing file
    base_path = model_path.rsplit('.', 1)[0]
    preprocessing_path = f"{base_path}_preprocessing.pkl"
    
    if os.path.exists(preprocessing_path):
        return joblib.load(preprocessing_path)
    
    # Try the model directory for a shared preprocessing file
    model_dir = os.path.dirname(model_path)
    shared_preprocessing = os.path.join(model_dir, 'preprocessing_v3.pkl')
    
    if os.path.exists(shared_preprocessing):
        return joblib.load(shared_preprocessing)
    
    return None
