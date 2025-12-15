from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import tempfile
import os
from .tasks import process_pdf_task

app = FastAPI(title="Pay Slip OCR Processor API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for output
app.mount("/media", StaticFiles(directory="output"), name="media")

@app.post("/process")
async def process_pdf(file: UploadFile = File(...)):
    """
    Upload a pay slip PDF file to process: split pages and rename based on employee info and period using OCR
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
            'status': 'Traitement en cours…',
            'detail': task.info.get('detail', ''),
            'progress': task.info.get('progress', ''),
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 0)
        }
    elif task.state == 'SUCCESS':
        response = {
            'task_id': task_id,
            'status': 'Completed',
            'output_dir': task.info['output_dir'],
            'file_count': task.info['file_count'],
            'employee_count': task.info.get('employee_count', 0)
        }
    else:  # FAILURE
        response = {
            'task_id': task_id,
            'status': 'Failed',
            'error': str(task.info)
        }

    return response

@app.get("/download/{task_id}")
async def download_results(task_id: str):
    """
    Get the processed pay slips organized by employee ID as folder structure
    """
    task = process_pdf_task.AsyncResult(task_id)

    if task.state != 'SUCCESS':
        return {"error": "Task is not completed or failed"}

    output_dir = task.info['output_dir']
    if not os.path.exists(output_dir):
        return {"error": "Processed files not found"}

    # Get the folder structure
    import glob
    structure = {}
    for employee_dir in os.listdir(output_dir):
        employee_path = os.path.join(output_dir, employee_dir)
        if os.path.isdir(employee_path):
            files = []
            for pdf_file in glob.glob(os.path.join(employee_path, "*.pdf")):
                files.append(os.path.basename(pdf_file))
            structure[employee_dir] = files

    return {
        "task_id": task_id,
        "output_dir": output_dir,
        "folder_structure": structure,
        "total_folders": len(structure),
        "total_files": sum(len(files) for files in structure.values())
    }
