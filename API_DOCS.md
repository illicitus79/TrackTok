# TrackTok API Documentation

## Overview

TrackTok provides a comprehensive REST API for multi-tenant expense tracking and project budget management. The API is built with Flask-smorest and follows OpenAPI 3.0 specifications.

## API Documentation

### Swagger UI (Interactive)

Access the interactive API documentation at:

```
http://localhost:5000/api/docs/swagger
```

Features:
- Browse all API endpoints
- View request/response schemas
- Test endpoints directly from the browser
- See authentication requirements
- View examples and descriptions

### ReDoc (Alternative Documentation)

A cleaner, read-only documentation interface:

```
http://localhost:5000/api/docs/redoc
```

### OpenAPI Specification

Download the raw OpenAPI JSON specification:

```
http://localhost:5000/api/docs/openapi.json
```

Or export to a file:

```bash
# Export OpenAPI spec
python scripts/export_openapi.py --openapi -o openapi.json

# Or use Makefile
make openapi
```

## Postman Collection

### Generate Postman Collection

Export a ready-to-use Postman collection:

```bash
# Export Postman collection
python scripts/export_openapi.py --postman -o postman_collection.json

# Or use Makefile
make postman

# Export both OpenAPI and Postman
python scripts/export_openapi.py --both
make docs
```

### Import to Postman

1. Open Postman
2. Click **Import** button (top left)
3. Select the `postman_collection.json` file
4. The collection will be imported with all endpoints organized by category

### Configure Collection Variables

After importing, set these collection variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | API base URL | `http://localhost:5000` |
| `jwt_token` | JWT access token | Obtained from login endpoint |
| `tenant_id` | Tenant ID | Your organization's tenant ID |

### Obtaining JWT Token

1. Use the **Authentication > Login** request
2. Provide credentials in request body
3. Copy the `access_token` from response
4. Paste into collection variable `jwt_token`
5. All authenticated requests will automatically include the token

## Authentication

### JWT Bearer Token

Most endpoints require JWT authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

### Obtaining Tokens

**Login Endpoint:**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### Refreshing Tokens

```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh-token>
```

## Multi-Tenancy

TrackTok supports two tenant resolution methods:

### 1. Subdomain-Based (Recommended)

Access the API via tenant-specific subdomain:

```
https://{tenant-slug}.tracktok.com/api/v1/...
```

Example:
```
https://acme.tracktok.com/api/v1/projects
```

### 2. Header-Based

Include the `X-Tenant-Id` header in requests:

```http
GET /api/v1/projects
X-Tenant-Id: 550e8400-e29b-41d4-a716-446655440000
Authorization: Bearer <token>
```

## Rate Limiting

API endpoints are rate limited to ensure fair usage:

| Endpoint Type | Limit |
|--------------|-------|
| Authentication | 10 requests/minute |
| Read operations (GET) | 100 requests/hour |
| Write operations (POST/PUT/PATCH/DELETE) | 50 requests/hour |

### Rate Limit Headers

Responses include rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1638360000
```

### Handling Rate Limits

When rate limited, you'll receive a `429 Too Many Requests` response:

```json
{
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Too many requests. Please try again later.",
  "retry_after": 3600
}
```

## Pagination

List endpoints return paginated results:

### Request Parameters

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `page` | integer | 1 | - | Page number |
| `per_page` | integer | 20 | 100 | Items per page |

### Example Request

```http
GET /api/v1/expenses?page=2&per_page=50
```

### Response Format

```json
{
  "items": [
    {
      "id": 1,
      "amount": 250.00,
      ...
    }
  ],
  "meta": {
    "page": 2,
    "per_page": 50,
    "total": 150,
    "pages": 3,
    "has_next": true,
    "has_prev": true,
    "next_page": 3,
    "prev_page": 1
  }
}
```

## Error Handling

### Standard Error Format

All errors follow a consistent structure:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "errors": {
    "field_name": ["Validation error message"]
  },
  "details": {
    "additional": "context"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required or invalid token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

### Validation Errors

Field-specific validation errors:

```json
{
  "code": "VALIDATION_ERROR",
  "message": "Validation failed",
  "errors": {
    "email": ["Invalid email format"],
    "amount": ["Must be greater than 0"]
  }
}
```

## Response Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource conflict |
| 422 | Unprocessable Entity | Validation failed |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service down |

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get tokens
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - Logout (invalidate token)

### Tenants
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant details
- `PATCH /api/v1/tenants/{id}` - Update tenant

### Users
- `GET /api/v1/users` - List users (paginated)
- `GET /api/v1/users/{id}` - Get user details
- `PATCH /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Deactivate user

### Projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects` - List projects (filtered, paginated)
- `GET /api/v1/projects/{id}` - Get project with aggregates
- `PATCH /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Expenses
- `POST /api/v1/expenses` - Create expense
- `GET /api/v1/expenses` - List expenses (filtered, paginated)
- `GET /api/v1/expenses/{id}` - Get expense details
- `PATCH /api/v1/expenses/{id}` - Update expense
- `DELETE /api/v1/expenses/{id}` - Delete expense

### Budgets
- `POST /api/v1/budgets` - Create budget
- `GET /api/v1/budgets` - List budgets
- `GET /api/v1/budgets/{id}` - Get budget details
- `PATCH /api/v1/budgets/{id}` - Update budget

### Reports
- `GET /api/v1/reports/project/{id}/summary` - Project summary
- `GET /api/v1/reports/project/{id}/category-breakdown` - Category breakdown
- `GET /api/v1/reports/project/{id}/monthly-trend` - Monthly trend
- `GET /api/v1/reports/tenant/cashflow` - Tenant cashflow
- `GET /api/v1/reports/export/csv` - Export to CSV
- `GET /api/v1/reports/export/xlsx` - Export to Excel

### Alerts
- `GET /api/v1/alerts` - List alerts
- `GET /api/v1/alerts/{id}` - Get alert details
- `PATCH /api/v1/alerts/{id}` - Mark alert as read
- `POST /api/v1/alerts/bulk/mark-read` - Bulk mark as read
- `GET /api/v1/alerts/stats` - Alert statistics

### Preferences
- `GET /api/v1/users/{id}/preferences` - Get user preferences
- `PATCH /api/v1/users/{id}/preferences` - Update preferences
- `GET /api/v1/users/me/preferences` - Get current user preferences

## Examples

### Create Expense

```http
POST /api/v1/expenses
Authorization: Bearer <token>
Content-Type: application/json

{
  "amount": 250.75,
  "currency": "USD",
  "expense_date": "2025-11-20",
  "vendor": "Figma Inc.",
  "note": "Design subscription",
  "project_id": 123,
  "is_project_related": true,
  "account_id": 45,
  "category_id": 9
}
```

### List Projects with Filters

```http
GET /api/v1/projects?status=active&page=1&per_page=20&search=website
Authorization: Bearer <token>
```

### Get Project Report

```http
GET /api/v1/reports/project/123/summary?from=2025-01-01&to=2025-11-30
Authorization: Bearer <token>
```

### Export Expenses to CSV

```http
GET /api/v1/reports/export/csv?project_id=123&from=2025-01-01&to=2025-11-30
Authorization: Bearer <token>
```

## Development

### Running Locally

```bash
# Start the development server
make dev

# Access Swagger UI
open http://localhost:5000/api/docs/swagger
```

### Generating Documentation

```bash
# Export OpenAPI spec
make openapi

# Export Postman collection
make postman

# Export both
make docs
```

### Testing API Endpoints

Use the Swagger UI to test endpoints interactively:

1. Navigate to `http://localhost:5000/api/docs/swagger`
2. Click **Authorize** button
3. Enter your JWT token
4. Browse endpoints and click **Try it out**
5. Fill in parameters and click **Execute**

## Support

For API support and questions:

- Documentation: `http://localhost:5000/api/docs/swagger`
- GitHub Issues: [github.com/tracktok/tracktok/issues]
- Email: support@tracktok.com
