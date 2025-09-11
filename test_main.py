import pytest
import requests
from fastapi.testclient import TestClient
from app import app 

client = TestClient(app)
DEPLOYED_URL = "https://citationconverter.duckdns.org/"

def test_root_get():
    response = client.get("/")
    assert response.status_code == 200

def test_cite_doi_existing():
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

def test_cite_doi_not_found():
    payload = {
        "identifier": "10.0000/invalid-doi",
        "type": "doi",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [404, 422]

def test_cite_isbn_valid():
    payload = {
        "identifier": "9780131101630",
        "type": "isbn",
        "style": "Harvard"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

def test_cite_isbn_invalid():
    payload = {
        "identifier": "0000000000000",
        "type": "isbn",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [404, 422]

def test_cite_missing_identifier():
    payload = {
        "type": "doi",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 422

def test_cite_unsupported_style():
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "Chicago"  # Assuming this style is not supported
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [400, 422]

def test_deployed_root_get():
    response = requests.get(f"{DEPLOYED_URL}/")
    assert response.status_code == 200

def test_deployed_cite_doi_existing():
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "APA"
    }
    response = requests.post(f"{DEPLOYED_URL}/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data
