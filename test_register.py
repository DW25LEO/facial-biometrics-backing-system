# test_register.py
import requests
import base64

# Test registration without face image first
test_data = {
    'username': 'testuser',
    'password': 'test123',
    'email': 'test@test.com',
    'full_name': 'Test User',
    'face_image': ''
}

try:
    response = requests.post('http://localhost:5000/api/register', json=test_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")