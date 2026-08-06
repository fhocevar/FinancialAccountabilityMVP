import os
os.environ["DATABASE_URL"]="sqlite:///./data/test.db"
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_health(): assert client.get('/health').json()=={'status':'ok'}
def test_login_and_pages():
    with client:
        r=client.post('/login',data={'email':'admin@local','password':'Admin123!'},follow_redirects=False)
        assert r.status_code==303
        assert client.get('/').status_code==200
        assert client.get('/meetings').status_code==200
        assert client.get('/clients').status_code==200
