from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_health_endpoint_returns_service_status(self):
        response = self.client.get(reverse("health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "service": "expense_tracker"})

    def test_health_endpoint_rejects_post(self):
        response = self.client.post(reverse("health"))

        self.assertEqual(response.status_code, 405)
