import sys
import os

# Add the project dir to path
sys.path.append(r"d:\Doc&S\i.zekiyev\Desktop\finance app\finflow")

from services.export_service import export_all_json

try:
    export_all_json("test_export.json", 1)
    print("Export successful!")
except Exception as e:
    print(f"Export failed: {e}")
    import traceback
    traceback.print_exc()
