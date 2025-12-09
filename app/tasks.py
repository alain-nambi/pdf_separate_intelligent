from celery import Celery
import tempfile
import os
import zipfile
import shutil
from .utils import split_pdf_one_page_per_file, process_single_page_pdf

app = Celery(
    'pdf_processor',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0',
    broker_connection_retry_on_startup=True
)

@app.task(bind=True)
def process_pdf_task(self, input_pdf_path: str):
    """
    Async task to process PDF: split, OCR rename, create ZIP
    """
    task_id = self.request.id

    try:
        # Create temp dirs for this task
        temp_base = tempfile.gettempdir()
        task_temp_dir = os.path.join(temp_base, f'pdf_task_{task_id}')
        pages_dir = os.path.join(task_temp_dir, 'pages')
        final_dir = os.path.join(task_temp_dir, 'final')

        os.makedirs(pages_dir, exist_ok=True)
        os.makedirs(final_dir, exist_ok=True)

        # Step 1: Split PDF
        self.update_state(state='PROGRESS', meta={'progress': 'Splitting PDF'})
        page_files = split_pdf_one_page_per_file(input_pdf_path, pages_dir)

        # Step 2: Process each page, OCR and rename
        renamed_files = []
        total_pages = len(page_files)
        for idx, page_file in enumerate(page_files):
            self.update_state(state='PROGRESS', meta={
                'progress': f'Renaming page {idx+1}/{total_pages}'
            })
            new_path = process_single_page_pdf(page_file, idx + 1, final_dir)
            renamed_files.append(new_path)

        # Step 3: Create ZIP
        self.update_state(state='PROGRESS', meta={'progress': 'Creating ZIP archive'})
        os.makedirs("output", exist_ok=True)
        zip_path = os.path.join("output", f'processed_pdfs_{task_id}.zip')
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in renamed_files:
                zipf.write(file, os.path.basename(file))

        # Clean up input
        os.remove(input_pdf_path)

        return {
            'status': 'SUCCESS',
            'zip_path': zip_path,
            'file_count': len(renamed_files)
        }

    except Exception as e:
        # Clean up on error
        if 'task_temp_dir' in locals() and os.path.exists(task_temp_dir):
            shutil.rmtree(task_temp_dir)
        if 'input_pdf_path' in locals() and os.path.exists(input_pdf_path):
            os.remove(input_pdf_path)
        raise Exception(f'Processing failed: {str(e)}')
