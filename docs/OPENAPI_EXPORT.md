# OpenAPI Export Script - Quick Reference

## Overview

The `scripts/export_openapi.py` script generates OpenAPI specifications and Postman collections from the TrackTok API.

## Usage

### Basic Commands

```bash
# Export OpenAPI specification only
python scripts/export_openapi.py --openapi

# Export Postman collection only
python scripts/export_openapi.py --postman

# Export both
python scripts/export_openapi.py --both

# Using Makefile shortcuts
make openapi    # Export OpenAPI spec
make postman    # Export Postman collection
make docs       # Export both
```

### Custom Output Paths

```bash
# Single format with custom output
python scripts/export_openapi.py --openapi -o api-spec.json
python scripts/export_openapi.py --postman -o my-collection.json

# Both formats with custom paths
python scripts/export_openapi.py --both \
  --openapi-file api-spec.json \
  --postman-file my-collection.json
```

### Help

```bash
python scripts/export_openapi.py --help
```

## Output Files

### OpenAPI Specification (`openapi.json`)

Generated file includes:

- All API endpoints with methods (GET, POST, PATCH, DELETE)
- Request/response schemas with validation rules
- Authentication schemes (Bearer JWT, Tenant Header)
- Server configurations (development, production)
- Error response schemas
- Pagination metadata schemas
- Detailed descriptions and examples
- Tags for endpoint organization

**Features:**

- OpenAPI 3.0.3 format
- Security schemes for JWT Bearer and X-Tenant-Id header
- Server variables for subdomain-based tenancy
- Comprehensive info section with usage guide
- Contact and license information
- Tagged endpoints (Authentication, Tenants, Users, Projects, etc.)

### Postman Collection (`postman_collection.json`)

Generated file includes:

- All API requests organized by tags/folders
- Pre-configured authorization (Bearer token)
- Collection variables (base_url, jwt_token, tenant_id)
- Request bodies with example payloads
- Query and path parameters
- Headers (Content-Type, X-Tenant-Id)
- Request descriptions

**Features:**

- Postman Collection v2.1 format
- Folder organization by API category
- Bearer token authentication at collection level
- Environment variables for easy configuration
- Example values for all parameters
- Disabled optional query parameters

## What Gets Exported

### From Flask-smorest

The script automatically extracts:

- Blueprint endpoints with @blp.route decorators
- Marshmallow schemas for requests/responses
- Response status codes (@blp.response decorators)
- Security requirements (@roles_required decorators)
- Path/query parameters
- Request body schemas

### Additional Metadata

The script enhances the spec with:

- Comprehensive API description (authentication, multi-tenancy, rate limiting)
- Server URLs for development and production
- Security scheme definitions
- Tag descriptions
- Contact information
- License information
- Error schema definitions

## OpenAPI Structure

```json
{
  "openapi": "3.0.3",
  "info": {
    "title": "TrackTok API",
    "version": "v1",
    "description": "...",
    "contact": {...},
    "license": {...}
  },
  "servers": [...],
  "paths": {
    "/api/v1/auth/login": {...},
    "/api/v1/expenses": {...},
    ...
  },
  "components": {
    "schemas": {...},
    "securitySchemes": {
      "bearerAuth": {...},
      "tenantHeader": {...}
    }
  },
  "tags": [...]
}
```

## Postman Collection Structure

```json
{
  "info": {
    "name": "TrackTok API",
    "version": "v1",
    "schema": "v2.1.0"
  },
  "auth": {
    "type": "bearer",
    "bearer": [{"key": "token", "value": "{{jwt_token}}"}]
  },
  "variable": [
    {"key": "base_url", "value": "http://localhost:5000"},
    {"key": "jwt_token", "value": ""},
    {"key": "tenant_id", "value": ""}
  ],
  "item": [
    {
      "name": "Authentication",
      "item": [...]
    },
    {
      "name": "Expenses",
      "item": [...]
    }
  ]
}
```

## Using the Exports

### OpenAPI Specification

**Use with Swagger UI:**

```html
<link
  rel="stylesheet"
  type="text/css"
  href="https://unpkg.com/swagger-ui-dist/swagger-ui.css"
/>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
<script>
  SwaggerUIBundle({
    url: "./openapi.json",
    dom_id: "#swagger-ui",
  });
</script>
```

**Use with API clients:**

- Import into Insomnia
- Generate client SDKs with OpenAPI Generator
- Validate API responses against spec
- Generate mock servers

**Use with documentation:**

- Generate static docs with Redoc
- Create API portals with Stoplight
- Validate against OpenAPI standards

### Postman Collection

**Import to Postman:**

1. Open Postman
2. Click **Import** (top left)
3. Select `postman_collection.json`
4. Collection appears in sidebar

**Configure Variables:**

1. Click collection name
2. Select **Variables** tab
3. Set current values:
   - `base_url`: Your API base URL
   - `jwt_token`: Get from `/api/v1/auth/login`
   - `tenant_id`: Your organization's tenant ID

**Test Endpoints:**

1. Select a request from folder
2. Review pre-filled parameters
3. Click **Send**
4. View response

**Share with Team:**

1. Export collection
2. Share JSON file
3. Team imports and uses same setup

## Integration Examples

### CI/CD Pipeline

```yaml
# .github/workflows/docs.yml
name: Update API Docs

on:
  push:
    branches: [main]

jobs:
  export-docs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Export OpenAPI
        run: python scripts/export_openapi.py --both
      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: api-docs
          path: |
            openapi.json
            postman_collection.json
```

### Documentation Site

```python
# docs/generate.py
import subprocess
import json

# Export OpenAPI spec
subprocess.run(["python", "scripts/export_openapi.py", "--openapi"])

# Generate HTML docs
with open("openapi.json") as f:
    spec = json.load(f)

# Use Redoc to generate static HTML
subprocess.run([
    "npx", "redoc-cli", "bundle", "openapi.json",
    "-o", "docs/api-reference.html"
])
```

### API Monitoring

```python
# tests/test_openapi_compliance.py
import json
from openapi_spec_validator import validate_spec

def test_openapi_compliance():
    with open("openapi.json") as f:
        spec = json.load(f)

    # Validate against OpenAPI 3.0 spec
    validate_spec(spec)
```

## Troubleshooting

### ImportError: No module named 'app'

**Solution:** Run from project root:

```bash
cd /path/to/TrackTok
python scripts/export_openapi.py
```

### ModuleNotFoundError: No module named 'redis'

**Solution:** Install dependencies:

```bash
pip install -r requirements.txt
```

### Export fails with Flask error

**Solution:** Ensure app factory works:

```bash
flask shell
>>> from app import create_app
>>> app = create_app('development')
```

### Empty paths in OpenAPI spec

**Solution:** Ensure blueprints are registered:

```python
# app/__init__.py
api.register_blueprint(auth.blp)
api.register_blueprint(expenses.blp)
# ... register all blueprints
```

### Postman collection missing requests

**Solution:** Check that endpoints have proper decorators:

```python
@blp.route("/expenses")
class ExpenseList(MethodView):
    @blp.response(200, ExpenseSchema(many=True))
    def get(self):
        # Method must be defined
        pass
```

## Advanced Usage

### Custom Server URLs

Edit `scripts/export_openapi.py`:

```python
openapi_dict["servers"] = [
    {
        "url": "https://api.yourdomain.com",
        "description": "Production"
    },
    {
        "url": "https://staging-api.yourdomain.com",
        "description": "Staging"
    }
]
```

### Custom Postman Examples

Add examples to OpenAPI spec:

```python
# In your schema
class ExpenseSchema(Schema):
    class Meta:
        example = {
            "amount": 250.75,
            "vendor": "Figma Inc.",
            "note": "Design subscription"
        }
```

### Filter Endpoints

Exclude certain paths from export:

```python
# In export_openapi.py
paths = {
    path: spec
    for path, spec in openapi_dict["paths"].items()
    if not path.startswith("/internal/")
}
openapi_dict["paths"] = paths
```

## Best Practices

1. **Regenerate regularly**: Run `make docs` after API changes
2. **Version your specs**: Commit exports to track API evolution
3. **Validate changes**: Use OpenAPI validators in CI/CD
4. **Document examples**: Add schema examples for better Postman imports
5. **Keep in sync**: Update script when adding new metadata
6. **Test exports**: Verify imports work in Postman/Swagger UI
7. **Share with team**: Distribute collections for consistent testing

## Resources

- [OpenAPI Specification](https://spec.openapis.org/oas/v3.0.3)
- [Postman Collection Format](https://schema.postman.com/)
- [Flask-smorest Documentation](https://flask-smorest.readthedocs.io/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)
- [ReDoc](https://github.com/Redocly/redoc)
