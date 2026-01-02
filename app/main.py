from fastapi import FastAPI
from mangum import Mangum

from app.api.routes import health, raffles, tickets
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="RifaApp API", version="1.0.0")
app.include_router(health.router)
app.include_router(raffles.router)
app.include_router(tickets.router)

handler = Mangum(app)
