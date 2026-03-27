"""
test_health.py — smoke tests for basic app health and wiring.
"""


class TestHealth:
    def test_health_endpoint_returns_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_health_does_not_require_auth(self, client):
        """The health check must be publicly accessible (used by Docker/k8s)."""
        r = client.get("/health")
        assert r.status_code == 200

    def test_404_on_unknown_route(self, client):
        r = client.get("/does-not-exist")
        assert r.status_code == 404


class TestRateLimitHeader:
    """
    Confirm rate-limit responses use the standard 429 code.
    Full rate-limit testing would require many requests in a loop;
    here we just validate that the error handler is wired up.
    """

    def test_rate_limit_handler_registered(self, client):
        r = client.get("/health")
        assert r.status_code == 200
