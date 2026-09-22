import os
import shutil
import tarfile
from datetime import datetime

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "backend", "trustforge.db")
CHROMA_PATH = os.path.join(BASE_DIR, "backend", "chroma_db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

def create_backup():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = os.path.join(BACKUP_DIR, f"trustforge_backup_{timestamp}.tar.gz")
    
    print(f"Creating backup at {backup_filename}...")
    
    with tarfile.open(backup_filename, "w:gz") as tar:
        if os.path.exists(DB_PATH):
            print(f"Adding {DB_PATH}")
            tar.add(DB_PATH, arcname="trustforge.db")
        else:
            print(f"Warning: Database {DB_PATH} not found.")
            
        if os.path.exists(CHROMA_PATH):
            print(f"Adding {CHROMA_PATH}")
            tar.add(CHROMA_PATH, arcname="chroma_db")
        else:
            print(f"Warning: ChromaDB {CHROMA_PATH} not found.")
            
    print("Backup complete.")

if __name__ == "__main__":
    create_backup()
