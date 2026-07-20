import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT))
os.environ["FLASK_TESTING"] = "1"
os.environ["NEW_AGENTS_CONFIG_ADMIN_ALLOW_UNAUTHENTICATED"] = "true"
os.environ["AI4SE_ENV"] = "test"
