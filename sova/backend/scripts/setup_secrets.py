import os
import secrets
import stat
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

def setup_secrets():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage_dir = os.path.join(backend_dir, "storage")
    os.makedirs(storage_dir, exist_ok=True)
    
    env_file = os.path.join(backend_dir, ".env")
    
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            if "SECRET_KEY=" in f.read():
                print("Secret key already exists in .env. Skipping.")
                return

    print("Generating new SECRET_KEY...")
    secret_key = secrets.token_hex(32)
    
    private_key_path = os.path.join(storage_dir, "private_key.pem")
    public_key_path = os.path.join(storage_dir, "public_key.pem")
    
    print("Generating Ed25519 signing keypair...")
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    with open(private_key_path, "wb") as f:
        f.write(private_pem)
        
    os.chmod(private_key_path, stat.S_IRUSR | stat.S_IWUSR)
    
    with open(public_key_path, "wb") as f:
        f.write(public_pem)
        
    env_content = f"""
APP_ENV=production
SECRET_KEY={secret_key}
SIGNING_PRIVATE_KEY_PATH={private_key_path}
SIGNING_PUBLIC_KEY_PATH={public_key_path}
"""
    
    with open(env_file, "a") as f:
        f.write(env_content)
        
    print("Secrets generated successfully.")

if __name__ == "__main__":
    setup_secrets()
