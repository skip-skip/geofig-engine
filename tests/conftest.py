import sys
from pathlib import Path

# Add src/geofig-engine to sys.path for imports
src_path = Path(__file__).parent.parent / "src" / "geofig-engine"
sys.path.insert(0, str(src_path))
