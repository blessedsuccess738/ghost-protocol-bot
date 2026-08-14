import os
import sys
import tempfile

# Ensure tests can import modules from the repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Use a temporary database for tests
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ghost_protocol_test.db")
if os.path.exists(TEST_DB_PATH):
    os.remove(TEST_DB_PATH)

os.environ["DATABASE_PATH"] = TEST_DB_PATH
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
