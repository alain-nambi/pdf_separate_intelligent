from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
import tempfile
import os
from .tasks import process_pdf_task

app = FastAPI(title="PDF Processor API")

@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    """
    Upload a PDF file to process: split pages and rename via OCR
    """
    if not file.filename.lower().endswith('.pdf'):
        return {"error": "Only PDF files are allowed"}

    # Save uploaded file to uploads folder
    import uuid
    file_id = str(uuid.uuid4())
    input_pdf_path = f"uploads/{file_id}.pdf"
    os.makedirs("uploads", exist_ok=True)
    with open(input_pdf_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Start async task
    task = process_pdf_task.delay(input_pdf_path)

    return {"task_id": task.id, "status": "Task started"}

@app.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get status of a processing task
    """
    task = process_pdf_task.AsyncResult(task_id)

    if task.state == 'PENDING':
        response = {
            'task_id': task_id,
            'status': 'Pending'
        }
    elif task.state == 'PROGRESS':
        response = {
            'task_id': task_id,
            'status': 'In Progress',
            'progress': task.info.get('progress', '')
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'status': 'Completed',
            'file_count': task.info['file_count']
        }
    else:  # FAILURE
        response = {
            'task_id': task_id,
            'status': 'Failed',
            'error': str(task.info)
        }

    return response

@app.get("/download/{task_id}")
async def download_zip(task_id: str):
    """
    Download the processed ZIP file for a completed task
    """
    task = process_pdf_task.AsyncResult(task_id)

    if task.state != 'SUCCESS':
        return {"error": "Task is not completed or failed"}

    zip_path = task.info['zip_path']
    if os.path.exists(zip_path):
        return FileResponse(zip_path, media_type='application/zip', filename='processed_pdfs.zip')
    else:
        return {"error": "ZIP file not found"}
