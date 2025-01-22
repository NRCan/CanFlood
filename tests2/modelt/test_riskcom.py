import pytest
import pandas as pd
import numpy as np
import logging
from model.riskcom import RiskModel

# Test cases for parameterization
test_cases = {
    "simple_case": {
        "aep_values": [0.1, 0.05, 0.01],
        "damage_values": [1000, 5000, 10000],
        "dx": 0.1,
        "expected_ev": 450.0,
    },
}

@pytest.fixture(scope="function")
def risk_model():
    """Fixture to create a properly initialized RiskModel instance."""
    model = RiskModel()
    model.prec = 2  # Precision for rounding
    model.integrate = "trapz"  # Integration method
    model.data_d = {}  # Mock data dictionary
    model.logger = logging.getLogger("RiskModel")  # Attach a logger
    return model

@pytest.fixture(scope="function")
def test_data(request):
    """Fixture to retrieve test-specific data."""
    return test_cases[request.param]

@pytest.mark.parametrize(
    "test_data", ["simple_case"], indirect=True  
)
def test_get_ev_with_parameters(risk_model, test_data):
    """Test _get_ev with parameterized inputs."""
    # Extract parameters from the test data
    aep_values = test_data["aep_values"]
    damage_values = test_data["damage_values"]
    dx = test_data["dx"]
    expected_ev = test_data["expected_ev"]

    # Input data
    ser = pd.Series(data=damage_values, index=aep_values)

    
    result = risk_model._get_ev(ser, dx=dx)

    # Assertion
    assert np.isclose(result, expected_ev, atol=1e-2), f"Expected {expected_ev}, got {result}"
