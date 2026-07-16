import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def disable_throttling():
    with patch('rest_framework.throttling.AnonRateThrottle.allow_request', return_value=True):
        with patch('rest_framework.throttling.UserRateThrottle.allow_request', return_value=True):
            with patch('apps.search.views.NearbySearchThrottle.allow_request', return_value=True):
                yield
