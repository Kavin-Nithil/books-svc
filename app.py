"""
Book Info Service
=================
Demonstrates REST, RPC, and GraphQL paradigms with FastAPI + Strawberry.

Install:
    pip install fastapi uvicorn strawberry-graphql[fastapi] pydantic

Run:
    uvicorn app:app --reload --port 8000

Explore:
    Swagger UI  → http://localhost:8000/docs
    ReDoc       → http://localhost:8000/redoc
    GraphiQL    → http://localhost:8000/graphql
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from strawberry.fastapi import GraphQLRouter

# ===========================================================
# Shared In-Memory Data Store
# ===========================================================

_books: dict[int, dict] = {
    1: {"id": 1, "title": "Clean Code",                "author": "Robert C. Martin",          "year": 2008, "genre": "Programming"},
    2: {"id": 2, "title": "The Pragmatic Programmer",  "author": "David Thomas & Andrew Hunt", "year": 1999, "genre": "Programming"},
    3: {"id": 3, "title": "Design Patterns",           "author": "Gang of Four",               "year": 1994, "genre": "Software Engineering"},
    4: {"id": 4, "title": "Introduction to Algorithms","author": "Cormen, Leiserson, Rivest",  "year": 2009, "genre": "Computer Science"},
    5: {"id": 5, "title": "The Mythical Man-Month",    "author": "Fred Brooks",                "year": 1975, "genre": "Software Engineering"},
}
_next_id = 6


def _alloc_id() -> int:
    global _next_id
    val = _next_id
    _next_id += 1
    return val


def _title_exists(title: str) -> bool:
    return any(b["title"].lower() == title.lower() for b in _books.values())


# ===========================================================
# Pydantic Schemas  (REST & RPC)
# ===========================================================

class BookOut(BaseModel):
    id:    int
    title: str
    author: str
    year:  int
    genre: str


class BookIn(BaseModel):
    title:  str = Field(..., min_length=1, examples=["Clean Code"])
    author: str = Field(..., min_length=1, examples=["Robert C. Martin"])
    year:   int = Field(..., ge=1000, le=2100, examples=[2008])
    genre:  str = Field(..., min_length=1, examples=["Programming"])


# ── RPC envelope ────────────────────────────────────────────

class RPCGetRequest(BaseModel):
    id: int = Field(..., examples=[1])


class RPCCreateRequest(BaseModel):
    title:  str = Field(..., examples=["Clean Code"])
    author: str = Field(..., examples=["Robert C. Martin"])
    year:   int = Field(..., examples=[2008])
    genre:  str = Field(..., examples=["Programming"])


class RPCDeleteRequest(BaseModel):
    id: int = Field(..., examples=[1])


# ===========================================================
# FastAPI App
# ===========================================================

app = FastAPI(
    title="Book Info Service",
    description=(
        "**Three API paradigms — one domain, one data store.**\n\n"
        "| Paradigm | Endpoints |\n"
        "|---|---|\n"
        "| **REST** | `GET /books`, `GET /books/{id}`, `POST /books`, `DELETE /books/{id}` |\n"
        "| **RPC** | `POST /rpc/getBook`, `POST /rpc/createBook`, `POST /rpc/deleteBook`, `POST /rpc/listBooks` |\n"
        "| **GraphQL** | `GET|POST /graphql` (GraphiQL included) |"
    ),
    version="1.0.0",
)


# ===========================================================
# PARADIGM 1 — REST
# Resource-oriented · HTTP verbs · standard status codes
# ===========================================================

@app.get(
    "/books",
    response_model=List[BookOut],
    tags=["REST"],
    summary="List all books",
    description="Returns every book. Optional `?genre=` filter (case-insensitive).",
)
def rest_list_books(genre: Optional[str] = None):
    results = list(_books.values())
    if genre:
        results = [b for b in results if b["genre"].lower() == genre.lower()]
    return results


@app.get(
    "/books/{book_id}",
    response_model=BookOut,
    tags=["REST"],
    summary="Get a book by ID",
    responses={404: {"description": "Book not found"}},
)
def rest_get_book(book_id: int):
    book = _books.get(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book with id={book_id} not found")
    return book


@app.post(
    "/books",
    response_model=BookOut,
    status_code=201,
    tags=["REST"],
    summary="Create a new book",
    responses={409: {"description": "Duplicate title"}},
)
def rest_create_book(payload: BookIn):
    if _title_exists(payload.title):
        raise HTTPException(status_code=409, detail=f"A book titled '{payload.title}' already exists")
    new_id = _alloc_id()
    book = {"id": new_id, **payload.model_dump()}
    _books[new_id] = book
    return book


@app.put(
    "/books/{book_id}",
    response_model=BookOut,
    tags=["REST"],
    summary="Update a book",
    responses={404: {"description": "Book not found"}},
)
def rest_update_book(book_id: int, payload: BookIn):
    if book_id not in _books:
        raise HTTPException(status_code=404, detail=f"Book with id={book_id} not found")
    # Allow same title if it belongs to this book
    for b in _books.values():
        if b["title"].lower() == payload.title.lower() and b["id"] != book_id:
            raise HTTPException(status_code=409, detail=f"Another book is already titled '{payload.title}'")
    _books[book_id] = {"id": book_id, **payload.model_dump()}
    return _books[book_id]


@app.delete(
    "/books/{book_id}",
    status_code=204,
    tags=["REST"],
    summary="Delete a book",
    responses={404: {"description": "Book not found"}},
)
def rest_delete_book(book_id: int):
    if book_id not in _books:
        raise HTTPException(status_code=404, detail=f"Book with id={book_id} not found")
    del _books[book_id]


# ===========================================================
# PARADIGM 2 — RPC
# Action-oriented · all POST · verb in URL · response envelope
# ===========================================================

def _rpc_ok(data) -> dict:
    """Standard RPC success envelope."""
    return {"success": True, "data": data, "error": None}


def _rpc_err(msg: str) -> dict:
    """Standard RPC failure envelope — always HTTP 200."""
    return {"success": False, "data": None, "error": msg}


@app.post(
    "/rpc/listBooks",
    tags=["RPC"],
    summary="[RPC] List all books",
    description=(
        "**RPC paradigm** — no request body needed.\n\n"
        "Always returns HTTP 200; success/failure lives inside the `success` field."
    ),
)
def rpc_list_books():
    books = [BookOut(**b).model_dump() for b in _books.values()]
    return _rpc_ok(books)


@app.post(
    "/rpc/getBook",
    tags=["RPC"],
    summary="[RPC] Get a book by ID",
    description="**RPC paradigm** — pass `{id}` in the JSON body.",
)
def rpc_get_book(req: RPCGetRequest):
    book = _books.get(req.id)
    if not book:
        return _rpc_err(f"Book with id={req.id} not found")
    return _rpc_ok(BookOut(**book).model_dump())


@app.post(
    "/rpc/createBook",
    tags=["RPC"],
    summary="[RPC] Create a book",
    description=(
        "**RPC paradigm** — pass all book fields in the body.\n\n"
        "HTTP status is always 200; check `success` for the outcome."
    ),
)
def rpc_create_book(req: RPCCreateRequest):
    if _title_exists(req.title):
        return _rpc_err(f"A book titled '{req.title}' already exists")
    new_id = _alloc_id()
    book = {"id": new_id, "title": req.title, "author": req.author, "year": req.year, "genre": req.genre}
    _books[new_id] = book
    return _rpc_ok(BookOut(**book).model_dump())


@app.post(
    "/rpc/deleteBook",
    tags=["RPC"],
    summary="[RPC] Delete a book",
    description="**RPC paradigm** — pass `{id}` in the JSON body.",
)
def rpc_delete_book(req: RPCDeleteRequest):
    if req.id not in _books:
        return _rpc_err(f"Book with id={req.id} not found")
    del _books[req.id]
    return _rpc_ok({"deleted_id": req.id})


# ===========================================================
# PARADIGM 3 — GraphQL  (Strawberry + FastAPI)
# Single endpoint · query language · client-driven field selection
# ===========================================================

@strawberry.type(description="Represents a book in the catalogue")
class BookType:
    id:     int
    title:  str
    author: str
    year:   int
    genre:  str


@strawberry.type
class DeleteResult:
    success:    bool
    deleted_id: Optional[int]
    message:    str


@strawberry.type
class Query:

    @strawberry.field(description="Fetch a single book by its numeric ID. Returns null if not found.")
    def book(self, id: int) -> Optional[BookType]:
        b = _books.get(id)
        return BookType(**b) if b else None

    @strawberry.field(description="List all books. Pass `genre` to filter (case-insensitive).")
    def books(self, genre: Optional[str] = None) -> List[BookType]:
        results = list(_books.values())
        if genre:
            results = [b for b in results if b["genre"].lower() == genre.lower()]
        return [BookType(**b) for b in results]

    @strawberry.field(description="Count total books, optionally filtered by genre.")
    def book_count(self, genre: Optional[str] = None) -> int:
        if genre:
            return sum(1 for b in _books.values() if b["genre"].lower() == genre.lower())
        return len(_books)


@strawberry.type
class Mutation:

    @strawberry.mutation(description="Create a new book. Raises an error if the title already exists.")
    def create_book(
        self,
        title:  str,
        author: str,
        year:   int,
        genre:  str,
    ) -> BookType:
        if _title_exists(title):
            raise ValueError(f"A book titled '{title}' already exists")
        new_id = _alloc_id()
        book = {"id": new_id, "title": title, "author": author, "year": year, "genre": genre}
        _books[new_id] = book
        return BookType(**book)

    @strawberry.mutation(description="Update an existing book by ID.")
    def update_book(
        self,
        id:     int,
        title:  str,
        author: str,
        year:   int,
        genre:  str,
    ) -> BookType:
        if id not in _books:
            raise ValueError(f"Book with id={id} not found")
        for b in _books.values():
            if b["title"].lower() == title.lower() and b["id"] != id:
                raise ValueError(f"Another book is already titled '{title}'")
        _books[id] = {"id": id, "title": title, "author": author, "year": year, "genre": genre}
        return BookType(**_books[id])

    @strawberry.mutation(description="Delete a book by ID. Returns a result object.")
    def delete_book(self, id: int) -> DeleteResult:
        if id not in _books:
            return DeleteResult(success=False, deleted_id=None, message=f"Book {id} not found")
        del _books[id]
        return DeleteResult(success=True, deleted_id=id, message="Book deleted successfully")


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, graphiql=True)
app.include_router(graphql_router, prefix="/graphql")


# ===========================================================
# Root / Health
# ===========================================================

@app.get("/", tags=["Health"], summary="Service info & endpoint map")
def root():
    return {
        "service": "Book Info Service",
        "version": "1.0.0",
        "total_books": len(_books),
        "paradigms": {
            "REST": {
                "description": "Resource-oriented, HTTP verbs, standard status codes",
                "endpoints": [
                    "GET    /books",
                    "GET    /books/{id}",
                    "POST   /books",
                    "PUT    /books/{id}",
                    "DELETE /books/{id}",
                ],
            },
            "RPC": {
                "description": "Action-oriented, all POST, response envelope {success, data, error}",
                "endpoints": [
                    "POST /rpc/listBooks",
                    "POST /rpc/getBook",
                    "POST /rpc/createBook",
                    "POST /rpc/deleteBook",
                ],
            },
            "GraphQL": {
                "description": "Single endpoint, client-driven field selection",
                "endpoint": "/graphql",
                "graphiql": "/graphql  (open in browser)",
                "queries":   ["book(id)", "books(genre?)", "bookCount(genre?)"],
                "mutations": ["createBook(...)", "updateBook(...)", "deleteBook(id)"],
            },
        },
        "docs": {
            "swagger": "/docs",
            "redoc":   "/redoc",
            "graphiql":"/graphql",
        },
    }

import multiprocessing

def run_app1():
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)

def run_app2():
    from artist_app import artist_app
    uvicorn.run("artist_app:artist_app", host="0.0.0.0", port=8001, reload=True)

if __name__ == "__main__":
    p1 = multiprocessing.Process(target=run_app1)
    p2 = multiprocessing.Process(target=run_app2)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
