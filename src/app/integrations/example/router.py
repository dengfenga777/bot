from fastapi import APIRouter

router = APIRouter(prefix="/api/example", tags=["example"])


@router.get("/ping")
def ping():
    return {"ok": True, "source": "integration-example"}

