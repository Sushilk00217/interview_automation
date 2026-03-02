import sys
import os
sys.path.append('e:/Coforge/AI-Interview/interview_automation/mock_backend')
try:
    from app.db.sql.models import Base
    print("Success importing Base and models")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
