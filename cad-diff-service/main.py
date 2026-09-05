from fastapi import FastAPI, UploadFile, File
from schemas import DiffResult
from services.classify import classify_file
from services.dxf_diff import diff_dxf
from services.image_diff import diff_images
from services.pdf_vector import diff_pdf_vector
import shutil, uuid, os

app = FastAPI()

UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_temp(file: UploadFile) -> str:
    safe_filename = os.path.basename(file.filename)  # strips any path components
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{safe_filename}")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return path

@app.post("/diff", response_model=DiffResult)
async def diff(revision_a: UploadFile = File(...), revision_b: UploadFile = File(...)):
    path_a = save_temp(revision_a)
    path_b = save_temp(revision_b)

    type_a = classify_file(path_a)
    type_b = classify_file(path_b)

    if type_a == "dxf" and type_b == "dxf":
        result = diff_dxf(path_a, path_b, type_a, type_b)
    elif type_a == "vector_pdf" and type_b == "vector_pdf":
        result = diff_pdf_vector(path_a, path_b)
    else:
        result = diff_images(path_a, path_b)

    return result