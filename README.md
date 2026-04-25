# books-svc
A python fastapi application for books-svc with simple CRUD APIs. Demonstrates 3 API Paradigms (Rest, Graphql and RPC).

## Kong Gateway

This repo now includes a DB-less Kong setup for:

- IP-based rate limiting on `app.py` routes (`/books`, `/rpc`, `/graphql`)
- Consumer-based rate limiting on `artist_app.py` routes (`/v1/artists`)
- Request size limiting on both upstream services

Files:

- `docker-compose.yaml` - starts Kong on `localhost:9000` (proxy) and `localhost:9001` (Admin API)
- `kong/kong.yaml` - declarative Kong configuration
- `postman-collection-kong.json` - Postman collection to test `200`, `401`, `413`, and `429` gateway scenarios

Run the backends first:

```bash
python3 app.py
```

Then start Kong:

```bash
docker compose up -d kong
```
