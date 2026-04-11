from cryptography.fernet import Fernet

# Der Schlüssel, den du eben generiert hast
key = b'G7cGxyUt7iaqtz_PRTurZGv3w0KDO83KET5mxfMcSPs=' 
cipher_suite = Fernet(key)

# Dein Passwort als Text
password = b"jOAkER,-,77LC"
encrypted_text = cipher_suite.encrypt(password)

print(f"Verschlüsseltes Passwort für die config.json:\n{encrypted_text.decode()}")
