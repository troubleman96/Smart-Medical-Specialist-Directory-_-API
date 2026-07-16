from rest_framework.test import APITestCase


class ThrottledTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        # Disable throttling in tests
        from rest_framework.settings import api_settings
        self._orig_throttle_classes = api_settings.DEFAULT_THROTTLE_CLASSES
        api_settings.DEFAULT_THROTTLE_CLASSES = []

    def tearDown(self):
        from rest_framework.settings import api_settings
        api_settings.DEFAULT_THROTTLE_CLASSES = self._orig_throttle_classes
        super().tearDown()
