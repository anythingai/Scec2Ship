import sys
from pathlib import Path

from dotenv import load_dotenv

# Add project root and packages to python path for tests
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "packages"))

# Load .env so GEMINI_API_KEY is available for integration tests
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
