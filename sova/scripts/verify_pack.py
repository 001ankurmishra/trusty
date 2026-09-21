#!/usr/bin/env python3
import sys
import zipfile
import hashlib
import base64
import os
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def verify_pack(zip_path, public_key_path):
    if not os.path.exists(zip_path):
        print(f"❌ Error: ZIP file {zip_path} not found.")
        sys.exit(1)
        
    if not os.path.exists(public_key_path):
        print(f"❌ Error: Public key {public_key_path} not found.")
        sys.exit(1)

    print(f"🔍 Verifying Signed Audit Pack: {zip_path}")
    
    with open(public_key_path, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            files = zipf.namelist()
            
            if "manifest.txt" not in files or "signature.b64" not in files:
                print("❌ Error: manifest.txt or signature.b64 missing from ZIP.")
                sys.exit(1)
                
            manifest = zipf.read("manifest.txt")
            sig_b64 = zipf.read("signature.b64").decode('utf-8').strip()
            
            try:
                signature = base64.b64decode(sig_b64)
                public_key.verify(signature, manifest)
                print("✅ Signature verified successfully.")
            except Exception as e:
                print(f"❌ FAILURE: Signature verification failed. {e}")
                sys.exit(1)
                
            print("🔍 Checking file hashes against manifest...")
            manifest_lines = manifest.decode('utf-8').strip().split('\n')
            for line in manifest_lines:
                if not line.strip():
                    continue
                expected_hash, filename = line.split("  ")
                if filename not in files:
                    print(f"❌ FAILURE: {filename} listed in manifest but missing from ZIP.")
                    sys.exit(1)
                
                file_content = zipf.read(filename)
                actual_hash = hashlib.sha256(file_content).hexdigest()
                if actual_hash != expected_hash:
                    print(f"❌ FAILURE: Hash mismatch for {filename}. Expected: {expected_hash}, Actual: {actual_hash}")
                    sys.exit(1)
                
                print(f"  ✅ {filename} matches expected hash.")
                
            print("\n✅ SUCCESS: The Signed Audit Pack is completely valid and untampered.")
    except zipfile.BadZipFile:
        print("❌ Error: Invalid ZIP file.")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python verify_pack.py <path_to_audit_pack.zip> <path_to_public_key.pem>")
        sys.exit(1)
    verify_pack(sys.argv[1], sys.argv[2])
