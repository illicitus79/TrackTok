#!/usr/bin/env python
"""
Export OpenAPI specification and generate Postman collection.

Usage:
    python scripts/export_openapi.py --output openapi.json
    python scripts/export_openapi.py --postman --output postman_collection.json
    python scripts/export_openapi.py --both --openapi-file openapi.json --postman-file postman.json
"""
import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app


def export_openapi(output_path: str = "openapi.json"):
    """
    Export OpenAPI specification to a JSON file.
    
    Args:
        output_path: Path to save the OpenAPI JSON file
    """
    app = create_app("development")
    
    with app.app_context():
        # Get OpenAPI spec from flask-smorest
        spec = app.extensions["flask-smorest"]["spec"]
        openapi_dict = spec.to_dict()
        
        # Add security schemes
        if "components" not in openapi_dict:
            openapi_dict["components"] = {}
        
        openapi_dict["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT access token obtained from /api/v1/auth/login"
            },
            "tenantHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Tenant-Id",
                "description": "Tenant ID for multi-tenant operations (alternative to subdomain)"
            }
        }
        
        # Add server information
        openapi_dict["servers"] = [
            {
                "url": "http://localhost:5000",
                "description": "Development server"
            },
            {
                "url": "https://{tenant}.tracktok.com",
                "description": "Production server (subdomain-based tenancy)",
                "variables": {
                    "tenant": {
                        "default": "demo",
                        "description": "Tenant subdomain"
                    }
                }
            }
        ]
        
        # Add info
        openapi_dict["info"]["description"] = """
# TrackTok API

Multi-tenant expense tracking and project budget management platform.

## Authentication

Obtain a JWT token by calling `POST /api/v1/auth/login` with your credentials:

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Include the token in subsequent requests using the `Authorization` header:

```
Authorization: Bearer <your-jwt-token>
```

## Multi-Tenancy

TrackTok supports two tenant resolution methods:

1. **Subdomain-based** (recommended): Access via `https://{tenant}.tracktok.com`
2. **Header-based**: Include `X-Tenant-Id` header in requests

## Rate Limiting

API endpoints are rate limited:
- Authentication endpoints: 10 requests per minute
- Read operations: 100 requests per hour
- Write operations: 50 requests per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Total requests allowed
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## Pagination

List endpoints return paginated results:

```json
{
  "items": [...],
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 150,
    "pages": 8,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

Query parameters:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

## Error Responses

All error responses follow a consistent format:

```json
{
  "code": "ERROR_CODE",
  "message": "Human-readable error message",
  "errors": {
    "field": ["Validation error"]
  },
  "details": {}
}
```

Common error codes:
- `VALIDATION_ERROR`: Request validation failed
- `UNAUTHORIZED`: Authentication required or token invalid
- `FORBIDDEN`: Insufficient permissions
- `NOT_FOUND`: Resource not found
- `CONFLICT`: Resource conflict (e.g., duplicate email)
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Response Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `204 No Content`: Successful request with no response body
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable
"""
        
        openapi_dict["info"]["contact"] = {
            "name": "TrackTok Support",
            "email": "support@tracktok.com",
            "url": "https://tracktok.com/support"
        }
        
        openapi_dict["info"]["license"] = {
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT"
        }
        
        # Add tags with descriptions
        openapi_dict["tags"] = [
            {
                "name": "Authentication",
                "description": "User authentication and token management"
            },
            {
                "name": "Tenants",
                "description": "Multi-tenant organization management"
            },
            {
                "name": "Users",
                "description": "User account management"
            },
            {
                "name": "Projects",
                "description": "Project and budget management"
            },
            {
                "name": "Expenses",
                "description": "Expense tracking and categorization"
            },
            {
                "name": "Budgets",
                "description": "Budget allocation and monitoring"
            },
            {
                "name": "Reports",
                "description": "Financial reports and analytics"
            },
            {
                "name": "Alerts",
                "description": "Notification and alert management"
            },
            {
                "name": "Preferences",
                "description": "User preferences and settings"
            }
        ]
        
        # Save to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(openapi_dict, f, indent=2, ensure_ascii=False)
        
        print(f"✓ OpenAPI specification exported to: {output_file.absolute()}")
        print(f"  Title: {openapi_dict['info']['title']}")
        print(f"  Version: {openapi_dict['info']['version']}")
        print(f"  Paths: {len(openapi_dict.get('paths', {}))}")
        print(f"  Schemas: {len(openapi_dict.get('components', {}).get('schemas', {}))}")
        
        return openapi_dict


def openapi_to_postman(openapi_dict: dict, output_path: str = "postman_collection.json"):
    """
    Convert OpenAPI specification to Postman Collection v2.1 format.
    
    Args:
        openapi_dict: OpenAPI specification dictionary
        output_path: Path to save the Postman collection file
    """
    info = openapi_dict.get("info", {})
    servers = openapi_dict.get("servers", [])
    paths = openapi_dict.get("paths", {})
    components = openapi_dict.get("components", {})
    
    # Create Postman collection structure
    collection = {
        "info": {
            "name": info.get("title", "API Collection"),
            "description": info.get("description", ""),
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_postman_id": "tracktok-api-collection",
            "version": info.get("version", "1.0.0")
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{jwt_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": servers[0]["url"] if servers else "http://localhost:5000",
                "type": "string"
            },
            {
                "key": "jwt_token",
                "value": "",
                "type": "string"
            },
            {
                "key": "tenant_id",
                "value": "",
                "type": "string"
            }
        ],
        "item": []
    }
    
    # Group endpoints by tag
    tag_groups = {}
    
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ["get", "post", "put", "patch", "delete"]:
                tags = operation.get("tags", ["Untagged"])
                tag = tags[0] if tags else "Untagged"
                
                if tag not in tag_groups:
                    tag_groups[tag] = []
                
                # Build request
                request = {
                    "name": operation.get("summary", f"{method.upper()} {path}"),
                    "request": {
                        "method": method.upper(),
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}" + path,
                            "host": ["{{base_url}}"],
                            "path": path.strip("/").split("/")
                        },
                        "description": operation.get("description", "")
                    },
                    "response": []
                }
                
                # Add tenant header if required
                if operation.get("security"):
                    request["request"]["header"].append({
                        "key": "X-Tenant-Id",
                        "value": "{{tenant_id}}",
                        "type": "text"
                    })
                
                # Add request body if present
                request_body = operation.get("requestBody", {})
                if request_body:
                    content = request_body.get("content", {})
                    if "application/json" in content:
                        schema = content["application/json"].get("schema", {})
                        example = content["application/json"].get("example", {})
                        
                        request["request"]["header"].append({
                            "key": "Content-Type",
                            "value": "application/json",
                            "type": "text"
                        })
                        
                        request["request"]["body"] = {
                            "mode": "raw",
                            "raw": json.dumps(example or schema, indent=2)
                        }
                
                # Add query parameters
                parameters = operation.get("parameters", [])
                query_params = [p for p in parameters if p.get("in") == "query"]
                if query_params:
                    request["request"]["url"]["query"] = []
                    for param in query_params:
                        request["request"]["url"]["query"].append({
                            "key": param["name"],
                            "value": str(param.get("example", "")),
                            "description": param.get("description", ""),
                            "disabled": not param.get("required", False)
                        })
                
                # Add path parameters
                path_params = [p for p in parameters if p.get("in") == "path"]
                if path_params:
                    if "variable" not in request["request"]["url"]:
                        request["request"]["url"]["variable"] = []
                    for param in path_params:
                        request["request"]["url"]["variable"].append({
                            "key": param["name"],
                            "value": str(param.get("example", "1")),
                            "description": param.get("description", "")
                        })
                
                tag_groups[tag].append(request)
    
    # Add grouped items to collection
    for tag, requests in sorted(tag_groups.items()):
        folder = {
            "name": tag,
            "item": requests
        }
        collection["item"].append(folder)
    
    # Save to file
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Postman collection exported to: {output_file.absolute()}")
    print(f"  Name: {collection['info']['name']}")
    print(f"  Folders: {len(collection['item'])}")
    print(f"  Total requests: {sum(len(folder['item']) for folder in collection['item'])}")
    print(f"\n  Import instructions:")
    print(f"  1. Open Postman")
    print(f"  2. Click 'Import' button")
    print(f"  3. Select the exported file: {output_file.name}")
    print(f"  4. Set collection variables:")
    print(f"     - base_url: Your API base URL")
    print(f"     - jwt_token: Obtain from /api/v1/auth/login")
    print(f"     - tenant_id: Your tenant ID")


def main():
    """Main entry point for the export script."""
    parser = argparse.ArgumentParser(
        description="Export OpenAPI specification and generate Postman collection"
    )
    
    parser.add_argument(
        "--openapi",
        action="store_true",
        help="Export OpenAPI specification only"
    )
    parser.add_argument(
        "--postman",
        action="store_true",
        help="Export Postman collection only"
    )
    parser.add_argument(
        "--both",
        action="store_true",
        help="Export both OpenAPI and Postman collection"
    )
    parser.add_argument(
        "--openapi-file",
        default="openapi.json",
        help="Output path for OpenAPI file (default: openapi.json)"
    )
    parser.add_argument(
        "--postman-file",
        default="postman_collection.json",
        help="Output path for Postman collection (default: postman_collection.json)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output path (used when exporting single format)"
    )
    
    args = parser.parse_args()
    
    # Determine what to export
    export_openapi_spec = args.openapi or args.both or not (args.openapi or args.postman)
    export_postman_collection = args.postman or args.both
    
    try:
        openapi_dict = None
        
        if export_openapi_spec:
            output_path = args.output if args.output and not args.both else args.openapi_file
            openapi_dict = export_openapi(output_path)
        
        if export_postman_collection:
            # Load OpenAPI if not already loaded
            if openapi_dict is None:
                app = create_app("development")
                with app.app_context():
                    spec = app.extensions["flask-smorest"]["spec"]
                    openapi_dict = spec.to_dict()
            
            output_path = args.output if args.output and not args.both else args.postman_file
            openapi_to_postman(openapi_dict, output_path)
        
        print("\n✓ Export completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Export failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
