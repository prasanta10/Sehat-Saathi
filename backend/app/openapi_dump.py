"""Print the OpenAPI document (used to generate the frontend's TypeScript types)."""

import json

from app.main import app

if __name__ == "__main__":
    print(json.dumps(app.openapi(), indent=1, sort_keys=True))
