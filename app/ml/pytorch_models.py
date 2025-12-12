"""
PyTorch model architectures for LSTM and GRU models.
These classes must match the architecture used during training.
"""

try:
    import torch
    import torch.nn as nn
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False


if TORCH_AVAILABLE:
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
            # Project input
            x = self.input_proj(x)
            x = self.input_norm(x)
            x = self.relu(x)
            
            # Add sequence dimension if needed
            if len(x.shape) == 2:
                x = x.unsqueeze(1)
            
            # GRU
            gru_out, _ = self.gru(x)
            out = gru_out[:, -1, :]  # Take last output
            
            # Output layers
            out = self.dropout(out)
            out = self.fc1(out)
            out = self.fc1_norm(out)
            out = self.relu(out)
            out = self.dropout(out)
            out = self.fc2(out)
            
            return out.squeeze()

else:
    # Provide dummy classes if PyTorch not available
    class ImprovedLSTMNetwork:
        pass
    
    class ImprovedGRUNetwork:
        pass
