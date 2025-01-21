import pytest
import pandas as pd
import numpy as np
from model.riskcom import RiskModel

@pytest.fixture
def risk_model():
    """Fixture to create a RiskModel instance with necessary attributes."""
    model = RiskModel()
    model.prec = 2  # Set precision for rounding
    model.integrate = 'trapz'  # Integration method
    return model

def test_get_ev_simple(risk_model):
    """Test _get_ev with a simple dataset."""
    # Input data
    aep_values = [0.1, 0.05, 0.01]
    damage_values = [1000, 5000, 10000]
    ser = pd.Series(data=damage_values, index=aep_values)
    
   
    expected_ev = 450.0  
    
    result = risk_model._get_ev(ser, dx=0.1)
    
    # Assertion
    assert np.isclose(result, expected_ev, atol=1e-2), f"Expected {expected_ev}, got {result}"