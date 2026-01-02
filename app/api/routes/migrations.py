from fastapi import APIRouter

from app.api.dependencies import require_db
from app.models.schemas import MigrationRunResponse
from app.services import migrations

router = APIRouter(prefix="/migrations", tags=["migrations"])


@router.post("/run", response_model=MigrationRunResponse)
def run_migrations():
    require_db()
    return migrations.run_migrations()
