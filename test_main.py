import pytest
import requests
from fastapi.testclient import TestClient
from app import app 

client = TestClient(app)
DEPLOYED_URL = "https://citationconverter.duckdns.org/"

# ---------------------------
# VALID INPUT TESTS
# ---------------------------

def test_root_get():
    """Test local root endpoint"""
    response = client.get("/")
    assert response.status_code == 200

def test_cite_doi_apa():
    """Test DOI citation in APA style"""
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

def test_cite_doi_harvard():
    """Test DOI citation in Harvard style"""
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "Harvard"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

def test_cite_doi_ieee():
    """Test DOI citation in IEEE style"""
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "IEEE"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

def test_cite_isbn_apa():
    """Test ISBN citation in APA style"""
    payload = {
        "identifier": "9780131101630",
        "type": "isbn",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

def test_cite_isbn_harvard():
    """Test ISBN citation in Harvard style"""
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

def test_cite_isbn_ieee():
    """Test ISBN citation in IEEE style"""
    payload = {
        "identifier": "9780131101630",
        "type": "isbn",
        "style": "IEEE"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data

# ---------------------------
# INVALID INPUT TESTS
# ---------------------------

def test_cite_doi_not_found():
    """Test invalid DOI identifier"""
    payload = {
        "identifier": "10.0000/invalid-doi",
        "type": "doi",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [404, 422]

def test_cite_isbn_invalid():
    """Test invalid ISBN identifier"""
    payload = {
        "identifier": "0000000000000",
        "type": "isbn",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [404, 422]

def test_cite_missing_identifier():
    """Test missing identifier field"""
    payload = {
        "type": "doi",
        "style": "APA"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code == 422

def test_cite_unsupported_style():
    """Test unsupported citation style"""
    payload = {
        "identifier": "10.1016/S1874-1029(13)60024-5",
        "type": "doi",
        "style": "Chicago"
    }
    response = client.post("/cite", json=payload)
    assert response.status_code in [400, 422]

# ---------------------------
# DEPLOYMENT (INTERNET) TESTS
# ---------------------------

def test_deployed_root_get():
    """Test deployed root endpoint"""
    response = requests.get(f"{DEPLOYED_URL}/")
    assert response.status_code == 200

def test_deployed_cite_doi_existing():
    """Test deployed system citation for DOI"""
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

def test_deployed_cite_isbn_existing():
    """Test deployed system citation for ISBN"""
    payload = {
        "identifier": "9780131101630",
        "type": "isbn",
        "style": "APA"
    }
    response = requests.post(f"{DEPLOYED_URL}/cite", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "citation" in data
    assert "in_text" in data
