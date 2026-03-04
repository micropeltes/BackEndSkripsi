from fastapi import APIRouter

router = APIRouter()

@router.get("/data")
def get_data():
    return {"message": "Data from backend"}