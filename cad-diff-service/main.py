from fastapi import FastAPI, UploadFile, File
from schemas import DiffResult
from services.classify import classify_file
from services.dxf_diff import diff_dxf
from services.image_diff import diff_images
import shutil, uuid, os

app = FastAPI()

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_temp(file: UploadFile) -> str:
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return path

@app.post("/diff", response_model=DiffResult)
async def diff(revision_a: UploadFile = File(...), revision_b: UploadFile = File(...)):
    path_a = save_temp(revision_a)
    path_b = save_temp(revision_b)

    type_a = classify_file(path_a)
    type_b = classify_file(path_b)

    if type_a in ("dxf", "vector_pdf") and type_b in ("dxf", "vector_pdf"):
        result = diff_dxf(path_a, path_b, type_a, type_b)
    else:
        result = diff_images(path_a, path_b)

    return result