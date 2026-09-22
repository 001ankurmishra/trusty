import os
import sys
import subprocess
import shutil
from pathlib import Path

def main():
    root_dir = Path(__file__).resolve().parent.parent
    build_dir = root_dir / "build"
    dist_zip = root_dir / "trustforge-offline-bundle.zip"
    
    print("========================================")
    print("   TrustForge - Offline Bundle Script   ")
    print("========================================")
    
    if build_dir.exists():
        print("Cleaning old build dir...")
        shutil.rmtree(build_dir)
    build_dir.mkdir()
    
    # 1. Build frontend
    print("\n[1/4] Building frontend...")
    frontend_dir = root_dir / "frontend"
    subprocess.run("npm install", shell=True, cwd=frontend_dir, check=True)
    subprocess.run("npm run build", shell=True, cwd=frontend_dir, check=True)
    
    # 2. Copy files to build directory
    print("\n[2/4] Copying backend and frontend dist...")
    backend_src = root_dir / "backend"
    backend_dest = build_dir / "backend"
    
    shutil.copytree(backend_src, backend_dest, ignore=shutil.ignore_patterns(
        "venv", ".venv", "__pycache__", "*.pyc", "*.db", "pytest_cache", ".pytest_cache"
    ))
    
    # Copy frontend dist to backend/dist so FastAPI can serve it
    frontend_dist_src = frontend_dir / "dist"
    frontend_dist_dest = backend_dest / "dist"
    shutil.copytree(frontend_dist_src, frontend_dist_dest)
    
    # Copy scripts
    scripts_dest = build_dir / "scripts"
    shutil.copytree(root_dir / "scripts", scripts_dest, ignore=shutil.ignore_patterns("bundle.*"))
    
    # Copy docs and README
    shutil.copytree(root_dir / "docs", build_dir / "docs")
    shutil.copy2(root_dir / "README.md", build_dir / "README.md")
    
    # 3. Create Wheelhouse for offline pip install
    print("\n[3/4] Downloading Python wheelhouse for offline installation...")
    wheelhouse_dir = build_dir / "wheelhouse"
    wheelhouse_dir.mkdir()
    subprocess.run([
        sys.executable, "-m", "pip", "download", 
        "-r", str(backend_dest / "requirements.txt"), 
        "-d", str(wheelhouse_dir)
    ], check=True)
    
    # Add offline install instructions
    with open(build_dir / "INSTALL_OFFLINE.txt", "w", encoding="utf-8") as f:
        f.write("""TrustForge Offline Installation (Windows)

1. Ensure Python 3.11+ and Ollama are installed on the target machine.
2. Open PowerShell as Administrator.
3. cd into this directory.
4. Run: python -m venv backend/venv
5. Run: backend/venv/Scripts/activate
6. Run: pip install --no-index --find-links=wheelhouse -r backend/requirements.txt
7. Run: powershell ./scripts/run_all.ps1

Note: The frontend is pre-built and will be served automatically on port 8000.
""")

    # 4. Zip the bundle
    print("\n[4/4] Zipping bundle...")
    shutil.make_archive(str(root_dir / "trustforge-offline-bundle"), "zip", str(build_dir))
    
    print("\nDone! Offline bundle created at:")
    print(dist_zip)

if __name__ == "__main__":
    main()
