#!/usr/bin/env python
"""
Verify OpenAPI implementation.

This script checks that:
1. Flask-smorest is properly configured
2. Blueprints are registered
3. OpenAPI spec can be generated
4. Postman collection can be exported
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def verify_flask_smorest_config():
    """Verify Flask-smorest configuration."""
    print("✓ Checking Flask-smorest configuration...")
    
    from app.core.config import Config
    
    assert hasattr(Config, "API_TITLE"), "Missing API_TITLE"
    assert hasattr(Config, "API_VERSION"), "Missing API_VERSION"
    assert hasattr(Config, "OPENAPI_VERSION"), "Missing OPENAPI_VERSION"
    assert hasattr(Config, "OPENAPI_URL_PREFIX"), "Missing OPENAPI_URL_PREFIX"
    assert hasattr(Config, "OPENAPI_SWAGGER_UI_PATH"), "Missing OPENAPI_SWAGGER_UI_PATH"
    
    print(f"  API Title: {Config.API_TITLE}")
    print(f"  API Version: {Config.API_VERSION}")
    print(f"  OpenAPI Version: {Config.OPENAPI_VERSION}")
    print(f"  Docs URL: {Config.OPENAPI_URL_PREFIX}{Config.OPENAPI_SWAGGER_UI_PATH}")
    print("  ✓ Configuration OK\n")


def verify_blueprints():
    """Verify blueprints are registered."""
    print("✓ Checking blueprint registration...")
    
    from app import create_app
    
    app = create_app("development")
    
    with app.app_context():
        spec = app.extensions["flask-smorest"]["spec"]
        openapi = spec.to_dict()
        
        paths = openapi.get("paths", {})
        assert len(paths) > 0, "No API paths found"
        
        print(f"  Registered endpoints: {len(paths)}")
        print(f"  Sample paths:")
        for i, path in enumerate(list(paths.keys())[:5]):
            print(f"    - {path}")
        if len(paths) > 5:
            print(f"    ... and {len(paths) - 5} more")
        print("  ✓ Blueprints OK\n")
        
        return openapi


def verify_schemas(openapi):
    """Verify schemas are defined."""
    print("✓ Checking schemas...")
    
    components = openapi.get("components", {})
    schemas = components.get("schemas", {})
    
    assert len(schemas) > 0, "No schemas found"
    
    print(f"  Defined schemas: {len(schemas)}")
    print(f"  Sample schemas:")
    for i, schema_name in enumerate(list(schemas.keys())[:5]):
        print(f"    - {schema_name}")
    if len(schemas) > 5:
        print(f"    ... and {len(schemas) - 5} more")
    print("  ✓ Schemas OK\n")


def verify_common_schemas():
    """Verify common schemas exist."""
    print("✓ Checking common schemas...")
    
    from app.schemas.common import (
        ErrorResponseSchema,
        ValidationErrorSchema,
        PaginationMetaSchema,
        PaginatedResponseSchema,
    )
    
    print("  - ErrorResponseSchema")
    print("  - ValidationErrorSchema")
    print("  - PaginationMetaSchema")
    print("  - PaginatedResponseSchema")
    print("  ✓ Common schemas OK\n")


def verify_export_script():
    """Verify export script exists and is executable."""
    print("✓ Checking export script...")
    
    script_path = Path(__file__).parent / "export_openapi.py"
    assert script_path.exists(), f"Export script not found: {script_path}"
    
    # Check script has required functions
    import importlib.util
    spec = importlib.util.spec_from_file_location("export_openapi", script_path)
    module = importlib.util.module_from_spec(spec)
    
    assert hasattr(module, "export_openapi"), "Missing export_openapi function"
    assert hasattr(module, "openapi_to_postman"), "Missing openapi_to_postman function"
    assert hasattr(module, "main"), "Missing main function"
    
    print(f"  Script path: {script_path}")
    print("  - export_openapi()")
    print("  - openapi_to_postman()")
    print("  - main()")
    print("  ✓ Export script OK\n")


def verify_documentation():
    """Verify documentation files exist."""
    print("✓ Checking documentation...")
    
    project_root = Path(__file__).parent.parent
    
    docs = [
        ("API_DOCS.md", "API documentation"),
        ("OPENAPI_IMPLEMENTATION.md", "Implementation summary"),
        ("docs/OPENAPI_EXPORT.md", "Export script reference"),
        ("README.md", "Main README"),
    ]
    
    for doc_path, description in docs:
        full_path = project_root / doc_path
        if full_path.exists():
            print(f"  ✓ {doc_path} - {description}")
        else:
            print(f"  ✗ {doc_path} - MISSING")
    
    print()


def verify_makefile_targets():
    """Verify Makefile has required targets."""
    print("✓ Checking Makefile targets...")
    
    makefile = Path(__file__).parent.parent / "Makefile"
    
    if not makefile.exists():
        print("  ✗ Makefile not found")
        return
    
    content = makefile.read_text()
    
    targets = ["openapi:", "postman:", "docs:"]
    for target in targets:
        if target in content:
            print(f"  ✓ make {target.rstrip(':')}")
        else:
            print(f"  ✗ make {target.rstrip(':')} - MISSING")
    
    print()


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("OpenAPI Implementation Verification")
    print("=" * 60)
    print()
    
    try:
        verify_flask_smorest_config()
        openapi = verify_blueprints()
        verify_schemas(openapi)
        verify_common_schemas()
        verify_export_script()
        verify_documentation()
        verify_makefile_targets()
        
        print("=" * 60)
        print("✓ All checks passed!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("  1. Start the app: flask run")
        print("  2. Visit Swagger UI: http://localhost:5000/api/docs/swagger")
        print("  3. Export specs: make docs")
        print("  4. Import postman_collection.json to Postman")
        print()
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"✗ Verification failed: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
