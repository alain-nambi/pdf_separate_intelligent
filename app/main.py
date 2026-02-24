from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import tempfile
import os
from .tasks import process_pdf_task
from .crypto import encrypt_file, decrypt_to_memory

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
    input_pdf_path = f"uploads/{file.filename}.pdf"


    print(f"DEBUG: Received file {file.filename}, saving to {input_pdf_path}")

    os.makedirs("uploads", exist_ok=True)
    # Save to temp first, then encrypt
    temp_path = f"{input_pdf_path}.temp"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Encrypt the file
    encrypt_file(temp_path, input_pdf_path)
    os.remove(temp_path)

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
            for enc_file in glob.glob(os.path.join(employee_path, "*.enc")):
                # Convert .enc back to .pdf for the API response
                pdf_filename = os.path.splitext(os.path.basename(enc_file))[0] + '.pdf'
                files.append(pdf_filename)
            structure[employee_dir] = files

    return {
        "task_id": task_id,
        "output_dir": output_dir,
        "folder_structure": structure,
        "total_folders": len(structure),
        "total_files": sum(len(files) for files in structure.values())
    }

@app.get("/folders")
async def get_folders():
    """
    Get the list of folder paths in the output directory
    """
    output_dir = "output"
    if not os.path.exists(output_dir):
        return {"folders": []}

    host_base = "C:/Projet/projet/pdf_separate_intelligent"
    folders = [os.path.join(host_base, "output", d) for d in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, d))]
    return {"folders": folders}

@app.get("/list_files/{folder_name}")
async def list_files_in_folder(folder_name: str):
    """
    Get the list of PDF files in a specific folder recursively
    """
    folder_path = os.path.join("output", folder_name)
    if not os.path.exists(folder_path):
        return {"files": []}

    pdf_files = []
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith('.enc'):
                # Convert .enc back to .pdf for the API response
                pdf_filename = os.path.splitext(file)[0] + '.pdf'
                # Get relative path from folder_path
                rel_path = os.path.relpath(os.path.join(root, pdf_filename), folder_path)
                pdf_files.append(rel_path)
    return {"files": pdf_files}

@app.get("/secure_file/{folder_name}/{file_name}")
async def get_secure_file(folder_name: str, file_name: str):
    """
    Serve an encrypted PDF file by decrypting it on the fly
    TODO: Add authentication to ensure only logged-in users can access
    """
    # Convert .pdf extension to .enc for the actual file path
    if file_name.lower().endswith('.pdf'):
        encrypted_filename = os.path.splitext(file_name)[0] + '.enc'
    else:
        encrypted_filename = file_name

    file_path = os.path.join("output", folder_name, encrypted_filename)
    if not os.path.exists(file_path) or not encrypted_filename.lower().endswith('.enc'):
        raise HTTPException(status_code=404, detail="File not found")

    try:
        # Decrypt to memory
        decrypted_data = decrypt_to_memory(file_path)

        # Return as file response with original filename
        from fastapi.responses import StreamingResponse
        import io

        return StreamingResponse(
            io.BytesIO(decrypted_data),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={file_name}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error decrypting file: {str(e)}")
