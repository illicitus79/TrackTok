"""Export OpenAPI specification."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app


def export_openapi():
    """Export OpenAPI spec to JSON file."""
    app = create_app()

    with app.app_context():
        from app.core.extensions import api

        spec = api.spec.to_dict()

        output_file = Path(__file__).parent.parent / "openapi.json"

        with open(output_file, "w") as f:
            json.dump(spec, f, indent=2)

        print(f"✅ OpenAPI specification exported to: {output_file}")


if __name__ == "__main__":
    export_openapi()
