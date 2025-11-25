"""Integration tests for API endpoints."""
import pytest
from flask import json


@pytest.mark.integration
class TestAuthAPI:
    """Test authentication API endpoints."""
    
    def test_login_success(self, client, tenant, user):
        """Test successful login."""
        response = client.post(
            '/api/v1/auth/login',
            headers={'X-Tenant-Id': tenant.id},
            json={
                'email': user.email,
                'password': 'Password123'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert 'refresh_token' in data
    
    def test_login_invalid_credentials(self, client, tenant, user):
        """Test login with invalid credentials."""
        response = client.post(
            '/api/v1/auth/login',
            headers={'X-Tenant-Id': tenant.id},
            json={
                'email': user.email,
                'password': 'WrongPassword'
            }
        )
        
        assert response.status_code == 401


@pytest.mark.integration
class TestExpensesAPI:
    """Test expense API endpoints."""
    
    def test_create_expense(self, client, auth_headers, tenant, user):
        """Test expense creation."""
        # First create a category
        category_response = client.post(
            '/api/v1/expenses/categories',
            headers=auth_headers,
            json={
                'name': 'Test Category',
                'color': '#FF0000'
            }
        )
        
        category_data = json.loads(category_response.data)
        category_id = category_data['id']
        
        # Create expense
        response = client.post(
            '/api/v1/expenses/',
            headers=auth_headers,
            json={
                'amount': '100.50',
                'title': 'Test Expense',
                'category_id': category_id,
                'expense_date': '2025-01-01',
                'payment_method': 'cash'
            }
        )
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['title'] == 'Test Expense'
        assert data['amount'] == '100.50'
    
    def test_get_expenses_list(self, client, auth_headers):
        """Test getting expenses list."""
        response = client.get(
            '/api/v1/expenses/',
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'expenses' in data
        assert 'pagination' in data
