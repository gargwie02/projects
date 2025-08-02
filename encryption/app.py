from flask import Flask, render_template, request, send_file
from cryptography.fernet import Fernet, InvalidToken
import os

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
KEY_FILE = "Secret.key"

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Generate a key if it doesn't exist
def generate_key():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as key_file:
            key_file.write(key)

# Load the secret key
def load_key():
    if os.path.exists(KEY_FILE):
        return open(KEY_FILE, "rb").read()
    else:
        return None

# Encrypt file
def encrypt_file(file_path, key):
    f = Fernet(key)
    with open(file_path, "rb") as file:
        encrypted_data = f.encrypt(file.read())
    
    encrypted_path = file_path + ".enc"
    with open(encrypted_path, "wb") as file:
        file.write(encrypted_data)
    
    return encrypted_path

# Decrypt file
def decrypt_file(file_path, key):
    f = Fernet(key)
    try:
        with open(file_path, "rb") as file:
            decrypted_data = f.decrypt(file.read())
        
        decrypted_path = file_path.replace(".enc", "")
        with open(decrypted_path, "wb") as file:
            file.write(decrypted_data)
        
        return decrypted_path
    except InvalidToken:
        return None

# Initialize key
generate_key()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/encrypt", methods=["POST"])
def encrypt():
    file = request.files["file"]
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        key = load_key()
        encrypted_path = encrypt_file(file_path, key)
        return send_file(encrypted_path, as_attachment=True)

    return "Encryption Failed", 400

@app.route("/decrypt", methods=["POST"])
def decrypt():
    file = request.files["file"]
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        key = load_key()
        decrypted_path = decrypt_file(file_path, key)

        if decrypted_path:
            return send_file(decrypted_path, as_attachment=True)
        else:
            return "Decryption Failed (Invalid Key or Corrupted File)", 400

if __name__ == "__main__":
    app.run(debug=True)
