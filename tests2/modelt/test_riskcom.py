import pytest
import numpy as np
from scipy import integrate
from unittest.mock import MagicMock, patch
import pandas as pd

class Plotr:
    pass

class Model:
    pass

class RiskModel(Plotr, Model):
    def __init__(self, integrate_method="trapz", precision=2):
        self.integrate = integrate_method
        self.prec = precision
        self.logger = MagicMock()  
        
    def _get_ev(self, ser, dx=0.1):
        """
        Calculate the integration using the specified method.
        """
        x = ser.tolist()  # Impacts
        y = ser.index.values.round(self.prec + 2).tolist()  # AEPs

        if self.integrate == "trapz":
            try:
                ead_tot = integrate.trapezoid(y, x=x, dx=dx)
            except AttributeError:
                try:
                    ead_tot = integrate.trapz(y, x=x, dx=dx)
                except AttributeError:
                    raise RuntimeError(
                        f"Integration failed. Ensure you have a compatible SciPy version."
                    )

        elif self.integrate == "simps":
            self.logger.warning("Integration method not tested")
            ead_tot = integrate.simps(y, x=x, dx=dx)

        else:
            raise ValueError(f"Integration method '{self.integrate}' not recognized")

        return round(ead_tot, self.prec)
    
# Fixtures for testing
@pytest.fixture
def risk_model():
    """Fixture to initialize the RiskModel class."""
    return RiskModel(integrate_method="trapz", precision=2)

@pytest.fixture
def test_series():
    """Fixture to provide a sample Pandas Series."""
    data = [0.1, 0.2, 0.3, 0.4, 0.5]
    index = [1, 2, 3, 4, 5]  # Example AEPs
    return pd.Series(data, index=index)

# Test cases
def test_get_ev_trapezoid(risk_model, test_series):
    """Test _get_ev with the trapezoid method."""
    risk_model.integrate = "trapz"
    result = risk_model._get_ev(test_series, dx=0.1)
    expected = integrate.trapezoid(
        test_series.index.values.tolist(),
        x=test_series.tolist(),
        dx=0.1
    )
    assert result == round(expected, risk_model.prec)
    
def test_get_ev_simps(risk_model, test_series):
    """Test _get_ev with the simps method."""
    risk_model.integrate = "simps"
    result = risk_model._get_ev(test_series, dx=0.1)
    expected = integrate.simps(
        test_series.index.values.tolist(),
        x=test_series.tolist(),
        dx=0.1
    )
    assert result == round(expected, risk_model.prec)

def test_get_ev_invalid_method(risk_model, test_series):
    """Test _get_ev with an invalid integration method."""
    risk_model.integrate = "invalid_method"
    with pytest.raises(ValueError, match="Integration method 'invalid_method' not recognized"):
        risk_model._get_ev(test_series)

def test_get_ev_trapz_fallback(risk_model, test_series):
    """Test _get_ev when falling back to trapz."""
    risk_model.integrate = "trapz"
    with patch("scipy.integrate.trapezoid", side_effect=AttributeError):
        result = risk_model._get_ev(test_series, dx=0.1)
        expected = integrate.trapz(
            test_series.index.values.tolist(),
            x=test_series.tolist(),
            dx=0.1
        )
        assert result == round(expected, risk_model.prec)

        
