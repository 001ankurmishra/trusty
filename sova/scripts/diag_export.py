import os
import zipfile
import psutil
import sqlite3
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "trustforge.db")
DIAG_DIR = os.path.join(BASE_DIR, "diagnostics")

def export_diagnostics():
    if not os.path.exists(DIAG_DIR):
        os.makedirs(DIAG_DIR)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = os.path.join(DIAG_DIR, f"trustforge_diagnostics_{timestamp}.zip")
    
    print(f"Creating diagnostic bundle: {zip_path}")
    
    sys_info = {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "ram_gb_total": round(psutil.virtual_memory().total / (1024**3), 2),
        "ram_gb_available": round(psutil.virtual_memory().available / (1024**3), 2),
    }
    
    db_stats = {}
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]
            for table in tables:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                db_stats[table] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            db_stats["error"] = str(e)
    else:
        db_stats["error"] = "Database not found."
        
    diag_data = {
        "system_info": sys_info,
        "database_stats": db_stats
    }
    
    diag_json_path = os.path.join(DIAG_DIR, "diag_info.json")
    with open(diag_json_path, "w") as f:
        json.dump(diag_data, f, indent=2)
        
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(diag_json_path, arcname="diag_info.json")
        if os.path.exists(DB_PATH):
            zipf.write(DB_PATH, arcname="trustforge.db")
            
    os.remove(diag_json_path)
    print("Export complete.")

if __name__ == "__main__":
    export_diagnostics()
