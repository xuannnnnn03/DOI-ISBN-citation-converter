from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import httpx, asyncio
import duckdb
import json

app = FastAPI()

# Connect to or create DuckDB database
con = duckdb.connect(database="db/citations.db", read_only=True)
con.execute("""
CREATE TABLE IF NOT EXISTS metadata_cache (
    identifier TEXT PRIMARY KEY,
    type TEXT,
    metadata JSON
)
""")

# Models
class CitationRequest(BaseModel):
    identifier: str
    type: str
    style: str

class CitationResponse(BaseModel):
    citation: str
    in_text: str

# Metadata fetchers with DuckDB cache
async def fetch_metadata_from_cache(identifier: str, id_type: str):
    result = con.execute("SELECT metadata FROM metadata_cache WHERE identifier = ? AND type = ?", (identifier, id_type)).fetchone()
    return json.loads(result[0]) if result else None

def store_metadata_in_cache(identifier: str, id_type: str, metadata: dict):
    con.execute("INSERT OR REPLACE INTO metadata_cache VALUES (?, ?, ?)", (identifier, id_type, metadata))

#Fetch metadata functions
async def fetch_doi_metadata(doi: str) -> dict:
    cached = await fetch_metadata_from_cache(doi, "doi")
    if cached:
        return cached
    url = f"https://api.crossref.org/works/{doi.strip()}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="DOI not found")
        metadata = r.json()["message"]
        store_metadata_in_cache(doi, "doi", metadata)
        return metadata

async def fetch_isbn_metadata(isbn: str) -> dict:
    cached = await fetch_metadata_from_cache(isbn, "isbn")
    if cached:
        return cached
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        if r.status_code != 200:
            raise HTTPException(status_code=404, detail="ISBN not found")
        d = r.json().get(f"ISBN:{isbn}", {})
        metadata = {
            "title": d.get("title", "Unknown Title"),
            "authors": [a["name"] for a in d.get("authors", [])] if "authors" in d else ["Unknown Author"],
            "publisher": d.get("publishers", [{}])[0].get("name", "Unknown Publisher"),
            "publish_date": d.get("publish_date", "Unknown Year"),
            "edition": d.get("edition_name", ""),
            "publish_places": d.get("publish_places", [])
        }
        store_metadata_in_cache(isbn, "isbn", metadata)
        return metadata

# Format helpers
def format_authors(authors, style, ieee=False):
    formatted = []
    for author in authors:
        if isinstance(author, dict):
            given = author.get("given", "")
            family = author.get("family", "").title()
            initials = "-".join([n[0] for n in given.split() if n]) + "." if given else ""
            formatted.append(f"{initials} {family}" if ieee else f"{family}, {initials}")
        else:
            parts = author.split()
            family = parts[-1].title()
            initials = "-".join(p[0] for p in parts[:-1]) + "."
            formatted.append(f"{initials} {family}" if ieee else f"{family}, {initials}")

    if ieee:
        return ", ".join(formatted[:-1]) + ", and " + formatted[-1] if len(formatted) > 2 else " and ".join(formatted)
    else:
        return ", ".join(formatted[:-1]) + " & " + formatted[-1] if len(formatted) > 2 else " & ".join(formatted)

def get_in_text_citation(authors, year):
    names = [a.get("family", "").title() if isinstance(a, dict) else a.split()[-1].title() for a in authors]
    return f"({names[0]}, {year})" if len(names) == 1 else f"({names[0]} & {names[1]}, {year})" if len(names) == 2 else f"({names[0]} et al., {year})"

def format_doi_citation(metadata, style, ref_index=1):
    authors = metadata.get("author", [])
    title = metadata.get("title", ["Unknown Title"])[0]
    journal = metadata.get("container-title", ["Unknown Journal"])[0]
    volume = metadata.get("volume", "")
    issue = metadata.get("issue", "")
    pages = metadata.get("page", "")
    year = metadata.get("issued", {}).get("date-parts", [[None]])[0][0]
    month = metadata.get("issued", {}).get("date-parts", [[None, None]])[0][1]
    doi = metadata.get("DOI", "")

    a = format_authors(authors, style, ieee=(style == "IEEE"))
    in_text = get_in_text_citation(authors, year)

    if style == "APA":
        citation = f"{a} ({year}). {title}. <em>{journal}</em>, {volume}({issue}), pp. {pages}. https://doi.org/{doi}"
    elif style == "Harvard":
        citation = f"{a}, {year}. {title}. <em>{journal}</em>, [e-journal] {volume}({issue}), pp. {pages}. https://doi.org/{doi}."
    elif style == "IEEE":
        citation = f"[{ref_index}] {a}, \u201c{title},\u201d {journal}, vol. {volume}, pp. {pages}, {month}. {year}. doi: {doi}."
    else:
        citation = "Error: Unsupported citation style"

    return citation, in_text

def format_isbn_citation(metadata, style, ref_index=1):
    authors = metadata.get("authors", [])
    title = metadata.get("title", "Unknown Title")
    edition = metadata.get("edition", "")
    publisher = metadata.get("publisher", "Unknown Publisher")
    year = metadata.get("publish_date", "Unknown Year")
    place = metadata.get("publish_places", [{}])[0].get("name", "Unknown Place") if metadata.get("publish_places") else "Unknown Place"

    a = format_authors(authors, style, ieee=(style == "IEEE"))
    in_text = get_in_text_citation(authors, year)

    if style == "APA":
        citation = f"{a} ({year}). <em>{title}</em>. {publisher}."
    elif style == "Harvard":
        edition_part = f" {edition}." if edition else ""
        citation = f"{a}, {year}. <em>{title}</em>.{edition_part} {place}: {publisher}."
    elif style == "IEEE":
        edition_part = f", {edition}" if edition else ""
        citation = f"[{ref_index}] {a}, \u201c{title}\u201d{edition_part}, {place}: {publisher}, {year}."
    else:
        citation = "Error: Unsupported citation style"

    return citation, in_text

# Routes
@app.get("/")
async def index():
    return FileResponse("index.html")

@app.post("/cite", response_model=CitationResponse)
async def cite(request: CitationRequest):
    if request.type == "doi":
        metadata = await fetch_doi_metadata(request.identifier)
        citation, in_text = format_doi_citation(metadata, request.style)
    elif request.type == "isbn":
        metadata = await fetch_isbn_metadata(request.identifier)
        citation, in_text = format_isbn_citation(metadata, request.style)
    else:
        raise HTTPException(status_code=400, detail="Invalid identifier type")
    return CitationResponse(citation=citation, in_text=in_text)

#Upload file
@app.post("/upload", response_model=List[CitationResponse])
async def upload_file(file: UploadFile = File(...), style: str = Form(...)):
    if not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="Only .txt files are supported.")

    content = await file.read()
    lines = [line.strip() for line in content.decode().splitlines() if line.strip()]

    async def process_line(line, index):
        if line.startswith("10.") or "/" in line:
            metadata = await fetch_doi_metadata(line)
            citation, in_text = format_doi_citation(metadata, style, ref_index=index)
        elif line.isdigit():
            metadata = await fetch_isbn_metadata(line)
            citation, in_text = format_isbn_citation(metadata, style, ref_index=index)
        else:
            return CitationResponse(citation=f"Invalid identifier: {line}", in_text="")
        return CitationResponse(citation=citation, in_text=in_text)

    tasks = [process_line(line, i + 1) for i, line in enumerate(lines)]
    return await asyncio.gather(*tasks)
