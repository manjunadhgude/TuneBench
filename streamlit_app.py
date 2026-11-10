"""Low-memory public entry point for Streamlit Community Cloud."""

import os
import runpy
from pathlib import Path

# The public instance offers rules and recorded evidence without native weights.
# Run app.py directly for the full local CPU-model interface.
os.environ["TUNEBENCH_PUBLIC_DEMO"] = "1"
runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
