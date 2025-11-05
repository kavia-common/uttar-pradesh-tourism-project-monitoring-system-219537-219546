import json
import os

from src.api.main import create_app

# Generate OpenAPI schema using app factory to avoid early imports
app = create_app()
openapi_schema = app.openapi()

# Write to interfaces/openapi.json
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
