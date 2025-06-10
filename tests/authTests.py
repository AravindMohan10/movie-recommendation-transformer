import sys
sys.path.append("backend/app") 
import warnings
warnings.filterwarnings("ignore")
from auth import hash_password, verify_password, create_access_token, decode_access_token

# Test password hashing & verification
raw_pw = "letmein"
hashed = hash_password(raw_pw)
assert verify_password("letmein", hashed)
assert not verify_password("wrongpw", hashed)

# Test JWT token creation & decoding
data = {"sub": "user123"}
token = create_access_token(data)
decoded = decode_access_token(token)
assert decoded["sub"] == "user123"
print("All auth tests passed! ")