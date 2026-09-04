import sys
import os
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import uvicorn
from app.config import settings

if __name__ == "__main__":
    port = int(os.environ.get("PORT", settings.PORT or settings.SERVER_PORT))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        reload_dirs=[str(backend_dir)],
    )
