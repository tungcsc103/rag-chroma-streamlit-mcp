from typing import BinaryIO, Dict, List
import PyPDF2
from docx import Document
import io
import mimetypes
import subprocess
import tempfile
import os
import shutil
from .text_splitter import TextChunker

class DocumentProcessor:
    def __init__(self):
        """Initialize document processor with text chunker."""
        self.text_chunker = TextChunker()

    @staticmethod
    def process_document(file: BinaryIO, filename: str) -> Dict[str, str]:
        """
        Process different types of documents and extract their text content.
        
        Args:
            file: File-like object containing the document
            filename: Name of the file
            
        Returns:
            Dict containing extracted text and metadata
        """
        processor = DocumentProcessor()
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            return processor._process_pdf(file)
        elif file_extension == 'docx':
            return processor._process_word(file)
        elif file_extension == 'doc':
            return processor._process_old_word(file, filename)
        elif file_extension in ['txt', 'md', 'csv']:
            return processor._process_text(file)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _process_pdf(self, file: BinaryIO) -> Dict[str, str]:
        """Process PDF files and extract text."""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = []
            metadata = {
                "title": pdf_reader.metadata.get("/Title", ""),
                "author": pdf_reader.metadata.get("/Author", ""),
                "subject": pdf_reader.metadata.get("/Subject", ""),
                "creator": pdf_reader.metadata.get("/Creator", ""),
                "page_count": len(pdf_reader.pages)
            }
            
            # Extract text from each page
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                if text.strip():
                    text_content.append(text)
            
            # Join all text content
            full_text = "\n\n".join(text_content)
            
            # Split text into chunks
            chunks = self.text_chunker.split_text(full_text, metadata)
            
            return {
                "chunks": chunks,
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Error processing PDF: {str(e)}")

    def _process_word(self, file: BinaryIO) -> Dict[str, str]:
        """Process Word documents and extract text."""
        try:
            temp_file = io.BytesIO(file.read())
            doc = Document(temp_file)
            text_content = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content.append(" | ".join(row_text))
            
            metadata = {
                "core_properties": {
                    "author": doc.core_properties.author or "",
                    "title": doc.core_properties.title or "",
                    "created": str(doc.core_properties.created or ""),
                    "modified": str(doc.core_properties.modified or "")
                }
            }
            
            # Join all text content
            full_text = "\n\n".join(text_content)
            
            # Split text into chunks
            chunks = self.text_chunker.split_text(full_text, metadata)
            
            return {
                "chunks": chunks,
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Error processing Word document: {str(e)}")

    def _process_old_word(self, file: BinaryIO, filename: str) -> Dict[str, str]:
        """Process old Word (.doc) documents using LibreOffice."""
        try:
            temp_base = os.getenv('TMPDIR', '/tmp/libreoffice')
            os.makedirs(temp_base, mode=0o1777, exist_ok=True)
            temp_dir = tempfile.mkdtemp(dir=temp_base)
            os.chmod(temp_dir, 0o1777)
            
            temp_input = os.path.join(temp_dir, "input.doc")
            
            try:
                with open(temp_input, 'wb') as f:
                    content = file.read()
                    f.write(content)
                os.chmod(temp_input, 0o666)
                
                env = os.environ.copy()
                env['HOME'] = '/root'
                env['PATH'] = f"/usr/lib/libreoffice/program:{env.get('PATH', '')}"
                
                result = subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'txt:Text', temp_input, '--outdir', temp_dir],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env
                )
                
                if result.returncode != 0:
                    raise ValueError(f"LibreOffice conversion failed: {result.stderr}")
                
                txt_path = os.path.join(temp_dir, "input.txt")
                if not os.path.exists(txt_path):
                    raise ValueError(f"Converted text file not found at {txt_path}")
                
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                if not text_content.strip():
                    raise ValueError("No text could be extracted from the document")
                
                metadata = {
                    "format": "doc",
                    "type": "Word 97-2004",
                    "conversion_method": "libreoffice",
                    "original_size": len(content)
                }
                
                # Split text into chunks
                chunks = self.text_chunker.split_text(text_content, metadata)
                
                return {
                    "chunks": chunks,
                    "metadata": metadata
                }
                
            finally:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
        except Exception as e:
            raise ValueError(f"Error processing Word 97-2004 document: {str(e)}")

    def _process_text(self, file: BinaryIO) -> Dict[str, str]:
        """Process text files and extract content."""
        try:
            content = file.read().decode('utf-8')
            metadata = {}
            
            # Split text into chunks
            chunks = self.text_chunker.split_text(content, metadata)
            
            return {
                "chunks": chunks,
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Error processing text file: {str(e)}")

    @staticmethod
    def get_supported_extensions() -> list:
        """Return list of supported file extensions."""
        return ['pdf', 'doc', 'docx', 'txt', 'md', 'csv'] 