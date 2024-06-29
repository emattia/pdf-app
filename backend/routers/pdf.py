from fastapi import APIRouter, File, UploadFile
import os
import base64


router = APIRouter()

# Global variable to store the current PDF filepath.
# CURRENT_CHAT_PDF = None
# Implies only one PDF can be processed at a time. 


@router.get("/hi-pdf")
async def hello():
    return {"message": "Hello PDF World"}


@router.post("/upload-pdf-url")
async def upload_pdf_from_url(url: str):
    # download PDF from URL
    # _process_pdf(pdf)
    pass


@router.post("/upload-pdf-file")
async def upload_pdf_from_file(uf: UploadFile):
    """
    UploadFile request makes a spooled file. 
    It does a kind of buffering, storing the file in memory to a size, then store it on disk.
    Read more: https://fastapi.tiangolo.com/tutorial/request-files/#file-parameters-with-uploadfile
    """
    print(uf.filename)
    if uf.content_type != 'application/pdf':
        return {"Error": 'Only PDF files are allowed!'}
    pdf_bytes = uf.file.read()
    pdf_file_path = f'data/{uf.filename}'
    if not os.path.exists('data'):
        os.makedirs('data')
    with open(pdf_file_path, 'wb') as f:
        f.write(pdf_bytes)
    CURRENT_CHAT_PDF = pdf_file_path
    # _process_pdf(pdf)
    return {
        'Handled': 'PDF file uploaded successfully!',
        'file_path': pdf_file_path
    }


def process_pdf(pdf_file):
    # process the PDF
    raise NotImplementedError