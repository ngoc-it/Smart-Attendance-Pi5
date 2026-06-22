import sys
import os
sys.path.append(os.getcwd())
from app import db

try:
    res = db.check_schedule_conflict(7, 1, 1, 2, 1)
    print(f"Result: {res}")
    if res is None:
        print("FAIL: Function returned None")
    else:
        valid, msg = res
        print(f"SUCCESS: valid={valid}, msg={msg}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
