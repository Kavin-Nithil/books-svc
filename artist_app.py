"""
Record Label Artists API
========================
Implements the OpenAPI 3.1.1 specification for the Record Label Artists API.

Endpoints:
    GET  /v1/artists              — Paginated list of artists (Basic Auth)
    POST /v1/artists              — Create a new artist    (Basic Auth)
    GET  /v1/artists/{artistName} — Get artist by name     (Basic Auth)

Run:
    pip install fastapi uvicorn
    uvicorn app:app --reload --port 8000

Docs:
    Swagger UI → http://localhost:8000/docs
    ReDoc      → http://localhost:8000/redoc
"""

import secrets
from typing import Annotated, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

# ===========================================================
# OpenAPI 3.1.1 Metadata
# ===========================================================

artist_app = FastAPI(
    title="Record Label Artists API",
    version="1.0.0",
    description=(
        "API for managing artists of a record label. "
        "Provides operations to list, create, and retrieve artists. "
        "Secured with **HTTP Basic authentication**."
    ),
    servers=[
        {"url": "http://localhost:8001",                      "description": "Local development server"},
        {"url": "https://api.recordlabel.example.com/v1",     "description": "Production server"},
    ],
    openapi_version="3.1.0",
)

# ===========================================================
# HTTP Basic Auth
# ===========================================================

security = HTTPBasic()

# Authorised users  (in production — load from a DB / secrets manager)
VALID_USERS: dict[str, str] = {
    "admin":    "secret123",
    "readonly": "readpass",
}


def verify_credentials(
    credentials: Annotated[HTTPBasicCredentials, Depends(security)],
) -> str:
    """
    Validates HTTP Basic credentials.
    Returns the authenticated username on success.
    Raises HTTP 401 on failure.
    """
    stored_password = VALID_USERS.get(credentials.username)

    # Use secrets.compare_digest to prevent timing attacks
    password_ok = stored_password is not None and secrets.compare_digest(
        credentials.password.encode("utf-8"),
        stored_password.encode("utf-8"),
    )

    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code":    "UNAUTHORIZED",
                "message": "Invalid username or password.",
            },
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username


# ===========================================================
# Pydantic Schemas  (mirrors OpenAPI components/schemas)
# ===========================================================

class Artist(BaseModel):
    """
    Schema: Artist
    Full representation of an artist stored in the label's database.
    """
    name:            str = Field(..., description="Full name of the artist.",                                    examples=["The Example Band"])
    genre:           str = Field(..., description="Primary musical genre of the artist.",                        examples=["Rock"])
    albumsPublished: int = Field(..., description="Number of albums the artist has released under the label.",   examples=[5], ge=0)
    username:        str = Field(..., description="Unique username for the artist within the label system.",      examples=["example_band"])

    model_config = {"json_schema_extra": {"example": {
        "name": "The Example Band",
        "genre": "Rock",
        "albumsPublished": 5,
        "username": "example_band",
    }}}


class NewArtist(BaseModel):
    """
    Schema: NewArtist
    Payload required when creating a new artist via POST /artists.
    """
    name:            str = Field(..., description="Full name of the artist.")
    genre:           str = Field(..., description="Primary musical genre of the artist.")
    albumsPublished: int = Field(..., description="Number of albums the artist has released under the label.", ge=0)
    username:        str = Field(..., description="Unique username for the artist within the label system.")

    model_config = {"json_schema_extra": {"example": {
        "name":            "Solar Groove",
        "genre":           "Jazz",
        "albumsPublished": 3,
        "username":        "solar_groove",
    }}}


class ArtistsPage(BaseModel):
    """
    Schema: ArtistsPage
    Paginated response returned by GET /artists.
    """
    items:  list[Artist] = Field(..., description="List of artists for the current page.")
    offset: int          = Field(..., description="Zero-based index of the first item in this page.", examples=[0])
    limit:  int          = Field(..., description="Maximum number of items returned in this page.",   examples=[20])
    total:  int          = Field(..., description="Total number of artists available.",                examples=[125])


class Error(BaseModel):
    """
    Schema: Error
    Generic error envelope returned on 4xx / 5xx responses.
    """
    code:    str                   = Field(..., description="Application-specific error code.",   examples=["INVALID_PARAMETER"])
    message: str                   = Field(..., description="Human-readable error message.",      examples=["The provided limit parameter is invalid."])
    details: Optional[dict]        = Field(None, description="Optional additional error details.")


# ===========================================================
# In-Memory Artist Database
# ===========================================================

_artists: list[dict] = [
    {"name": "Arctic Beats",  "genre": "Electronic",         "albumsPublished": 3,  "username": "arctic_beats"},
    {"name": "Solar Groove",  "genre": "Jazz",               "albumsPublished": 7,  "username": "solar_groove"},
    {"name": "Urban Echoes",  "genre": "Hip-Hop",            "albumsPublished": 2,  "username": "urban_echoes"},
    {"name": "Velvet Storm",  "genre": "Rock",               "albumsPublished": 5,  "username": "velvet_storm"},
    {"name": "Neon Pulse",    "genre": "Pop",                "albumsPublished": 1,  "username": "neon_pulse"},
    {"name": "Amber Tide",    "genre": "Folk",               "albumsPublished": 4,  "username": "amber_tide"},
    {"name": "Phantom Keys",  "genre": "Classical Fusion",   "albumsPublished": 6,  "username": "phantom_keys"},
    {"name": "Dusk Circuit",  "genre": "Ambient",            "albumsPublished": 2,  "username": "dusk_circuit"},
]


def _find_by_name(name: str) -> Optional[dict]:
    """Case-insensitive artist lookup by name."""
    return next(
        (a for a in _artists if a["name"].lower() == name.lower()),
        None,
    )


def _find_by_username(username: str) -> Optional[dict]:
    """Case-insensitive artist lookup by username."""
    return next(
        (a for a in _artists if a["username"].lower() == username.lower()),
        None,
    )


# ===========================================================
# Shared Error Responses (reused across all endpoints)
# ===========================================================

_ERROR_RESPONSES = {
    401: {"model": Error, "description": "Missing or invalid authentication credentials."},
    500: {"model": Error, "description": "Unexpected server error."},
}


# ===========================================================
# Routes — /v1/artists
# ===========================================================

@artist_app.get(
    "/v1/artists",
    response_model=ArtistsPage,
    status_code=status.HTTP_200_OK,
    tags=["Artists"],
    summary="List artists",
    description=(
        "Returns a **paginated** list of artists. "
        "Control pagination with `offset` (zero-based start index) "
        "and `limit` (page size, 1–100)."
    ),
    operation_id="listArtists",
    responses={
        200: {"model": ArtistsPage, "description": "Successful retrieval of artists list."},
        400: {"model": Error,       "description": "Invalid query parameters (e.g., negative offset, invalid limit)."},
        **_ERROR_RESPONSES,
    },
)
def list_artists(
    offset: Annotated[int, Query(ge=0,  description="Zero-based index of the first artist to return.", example=0)]  = 0,
    limit:  Annotated[int, Query(ge=1, le=100, description="Maximum number of artists to return (1–100).", example=20)] = 20,
    _username: str = Depends(verify_credentials),
) -> ArtistsPage:
    """
    **GET /v1/artists**

    Returns a paginated slice of the artist catalogue.

    - **offset** — skip this many artists from the beginning (default 0)
    - **limit**  — return at most this many artists (default 20, max 100)

    Secured with HTTP Basic authentication.
    """
    page = _artists[offset : offset + limit]

    return ArtistsPage(
        items=  [Artist(**a) for a in page],
        offset= offset,
        limit=  limit,
        total=  len(_artists),
    )


@artist_app.post(
    "/v1/artists",
    response_model=Artist,
    status_code=status.HTTP_201_CREATED,
    tags=["Artists"],
    summary="Create an artist",
    description="Adds a **new artist** to the record label's database.",
    operation_id="createArtist",
    responses={
        201: {"model": Artist, "description": "Artist successfully created."},
        400: {"model": Error,  "description": "Validation error in the provided artist data."},
        409: {"model": Error,  "description": "Artist with the same name or username already exists."},
        **_ERROR_RESPONSES,
    },
)
def create_artist(
    payload: NewArtist,
    _username: str = Depends(verify_credentials),
) -> Artist:
    """
    **POST /v1/artists**

    Creates a new artist record. Both `name` and `username` must be unique.

    - Returns **201 Created** with the saved artist on success.
    - Returns **409 Conflict** if `name` or `username` is already taken.
    - Returns **400 Bad Request** if required fields are missing or invalid.

    Secured with HTTP Basic authentication.
    """
    # Duplicate name check
    if _find_by_name(payload.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code":    "CONFLICT",
                "message": f"An artist named '{payload.name}' already exists.",
                "details": {"field": "name", "value": payload.name},
            },
        )

    # Duplicate username check
    if _find_by_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code":    "CONFLICT",
                "message": f"The username '{payload.username}' is already taken.",
                "details": {"field": "username", "value": payload.username},
            },
        )

    new_artist = payload.model_dump()
    _artists.append(new_artist)
    return Artist(**new_artist)


@artist_app.get(
    "/v1/artists/{artistName}",
    response_model=Artist,
    status_code=status.HTTP_200_OK,
    tags=["Artists"],
    summary="Get artist by name",
    description="Returns a **specific artist's** information identified by their name.",
    operation_id="getArtistByName",
    responses={
        200: {"model": Artist, "description": "Artist found and returned successfully."},
        404: {"model": Error,  "description": "No artist found with the provided name."},
        **_ERROR_RESPONSES,
    },
)
def get_artist_by_name(
    artistName: str,
    _username: str = Depends(verify_credentials),
) -> Artist:
    """
    **GET /v1/artists/{artistName}**

    Retrieves a single artist by their full name (case-insensitive).

    - Returns **200 OK** with the artist object on success.
    - Returns **404 Not Found** if no artist matches the provided name.

    Secured with HTTP Basic authentication.
    """
    artist = _find_by_name(artistName)

    if not artist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code":    "NOT_FOUND",
                "message": f"No artist found with name '{artistName}'.",
                "details": {"artistName": artistName},
            },
        )

    return Artist(**artist)


# ===========================================================
# Health Check (unauthenticated)
# ===========================================================

@artist_app.get("/health", tags=["Health"], summary="Health check", include_in_schema=False)
def health():
    return {"status": "ok", "total_artists": len(_artists)}


# ===========================================================
# Entry Point
# ===========================================================

if __name__ == "__main__":
    uvicorn.run("artist_app:artist_app", host="0.0.0.0", port=8001, reload=True)