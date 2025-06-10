#!/usr/bin/env python3
"""Quick test for login endpoint. Run with backend up: python tests/test_login.py"""
import requests
import sys

def main():
    try:
        response = requests.post(
            "http://localhost:8000/api/login",
            data={"username": "testuser", "password": "testpass123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5,
        )
        print("Status:", response.status_code)
        if response.status_code == 200:
            print("Login OK")
        else:
            print("Response:", response.json())
    except requests.exceptions.ConnectionError:
        print("Backend not running. Start: cd backend && uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

if __name__ == "__main__":
    main()
