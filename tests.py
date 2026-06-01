"""
Pytest test suite for Vampiro da Recorrência application.
Run with: pytest tests.py -v
"""

import pytest
from app import create_app
from models import db, User
from config import TestingConfig
from datetime import datetime


@pytest.fixture
def app():
    """Create and configure a test app."""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's CLI."""
    return app.test_cli_runner()


class TestAppCreation:
    """Test application creation and configuration."""
    
    def test_app_is_created(self, app):
        assert app is not None
    
    def test_app_is_testing(self, app):
        assert app.config['TESTING'] is True
    
    def test_app_has_secret_key(self, app):
        assert app.config['SECRET_KEY'] is not None


class TestAuthRoutes:
    """Test authentication routes."""
    
    def test_login_page_loads(self, client):
        response = client.get('/login')
        assert response.status_code == 200
        assert b'Entre no Vampiro' in response.data
    
    def test_register_page_loads(self, client):
        response = client.get('/register')
        assert response.status_code == 200
        assert b'Criar conta' in response.data
    
    def test_register_user(self, client):
        response = client.post('/register', data={
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
        }, follow_redirects=True)
        assert response.status_code == 200
    
    def test_login_with_credentials(self, client):
        # First register
        client.post('/register', data={
            'name': 'Test User',
            'email': 'test@example.com',
            'password': 'password123',
            'password_confirm': 'password123',
        })
        
        # Then login
        response = client.post('/login', data={
            'email': 'test@example.com',
            'password': 'password123',
        }, follow_redirects=True)
        assert response.status_code == 200


class TestPublicRoutes:
    """Test public routes."""
    
    def test_index_redirects_when_not_logged_in(self, client):
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302
        assert '/login' in response.location


class TestCSRFProtection:
    """Test CSRF protection."""
    
    def test_csrf_token_present_in_form(self, client):
        response = client.get('/register')
        assert response.status_code == 200
        assert b'csrf_token' in response.data


class TestErrorHandlers:
    """Test error handlers."""
    
    def test_404_error_handler(self, client):
        response = client.get('/nonexistent')
        assert response.status_code == 404
    
    def test_error_page_loads(self, client):
        response = client.get('/nonexistent')
        assert b'error' in response.data.lower() or b'n' in response.data.lower()


class TestSecurity:
    """Test security features."""
    
    def test_session_cookie_httponly(self, app):
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
    
    def test_session_cookie_samesite(self, app):
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200


# Performance tests
class TestPerformance:
    """Test application performance."""
    
    def test_index_page_loads_fast(self, client):
        import time
        start = time.time()
        response = client.get('/login')
        elapsed = time.time() - start
        assert elapsed < 1.0, f"Page load took {elapsed}s, expected < 1.0s"
        assert response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
