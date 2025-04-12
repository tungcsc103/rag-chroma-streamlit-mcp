from typing import BinaryIO, Dict
import PyPDF2
from docx import Document
import io
import mimetypes
import subprocess
import tempfile
import os
import shutil

class DocumentProcessor:
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
        file_extension = filename.lower().split('.')[-1]
        
        if file_extension == 'pdf':
            return DocumentProcessor._process_pdf(file)
        elif file_extension == 'docx':
            return DocumentProcessor._process_word(file)
        elif file_extension == 'doc':
            return DocumentProcessor._process_old_word(file, filename)
        elif file_extension in ['txt', 'md', 'csv']:
            return DocumentProcessor._process_text(file)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    @staticmethod
    def _process_pdf(file: BinaryIO) -> Dict[str, str]:
        """Process PDF files and extract text."""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text_content = []
            metadata = {}
            
            # Extract text from each page
            for page in pdf_reader.pages:
                text_content.append(page.extract_text())
            
            # Get PDF metadata if available
            if pdf_reader.metadata:
                metadata = {
                    "title": pdf_reader.metadata.get("/Title", ""),
                    "author": pdf_reader.metadata.get("/Author", ""),
                    "subject": pdf_reader.metadata.get("/Subject", ""),
                    "creator": pdf_reader.metadata.get("/Creator", ""),
                    "page_count": len(pdf_reader.pages)
                }
            
            return {
                "text": "\n".join(text_content),
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Error processing PDF: {str(e)}")

    @staticmethod
    def _process_word(file: BinaryIO) -> Dict[str, str]:
        """Process Word documents and extract text."""
        try:
            # Create a temporary BytesIO object to handle the file
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
            
            return {
                "text": "\n".join(text_content),
                "metadata": metadata
            }
        except Exception as e:
            raise ValueError(f"Error processing Word document: {str(e)}")

    @staticmethod
    def _process_old_word(file: BinaryIO, filename: str) -> Dict[str, str]:
        """Process old Word (.doc) documents (Word 97-2004 format).
        
        Args:
            file: File-like object containing the document
            filename: Original filename of the document
            
        Returns:
            Dict containing extracted text and metadata
        """
        try:
            # Get temp directory from environment or use default
            temp_base = os.getenv('TMPDIR', '/tmp/libreoffice')
            
            # Ensure temp directory exists with correct permissions
            os.makedirs(temp_base, mode=0o1777, exist_ok=True)
            
            # Create a temporary directory for this conversion
            temp_dir = tempfile.mkdtemp(dir=temp_base)
            os.chmod(temp_dir, 0o1777)  # Ensure directory is writable
            
            temp_input = os.path.join(temp_dir, "input.doc")
            
            try:
                # Save the input file
                with open(temp_input, 'wb') as f:
                    content = file.read()
                    f.write(content)
                os.chmod(temp_input, 0o666)  # Ensure file is readable/writable
                
                print(f"Converting Word 97-2004 document using LibreOffice...")
                print(f"Temp directory: {temp_dir}")
                print(f"Input file: {temp_input}")
                
                # Set up environment for LibreOffice
                env = os.environ.copy()
                env['HOME'] = '/root'  # Ensure HOME is set
                env['PATH'] = f"/usr/lib/libreoffice/program:{env.get('PATH', '')}"
                
                # Convert to text using LibreOffice
                result = subprocess.run(
                    ['soffice', '--headless', '--convert-to', 'txt:Text', temp_input, '--outdir', temp_dir],
                    capture_output=True,
                    text=True,
                    check=False,
                    env=env
                )
                
                print(f"LibreOffice conversion output: {result.stdout}")
                if result.stderr:
                    print(f"LibreOffice conversion errors: {result.stderr}")
                
                if result.returncode != 0:
                    raise ValueError(f"LibreOffice conversion failed: {result.stderr}")
                
                # Read the converted text file
                txt_path = os.path.join(temp_dir, "input.txt")
                if not os.path.exists(txt_path):
                    # List directory contents for debugging
                    print(f"Directory contents: {os.listdir(temp_dir)}")
                    raise ValueError(f"Converted text file not found at {txt_path}")
                
                with open(txt_path, 'r', encoding='utf-8') as f:
                    text_content = f.read()
                
                if not text_content.strip():
                    raise ValueError("No text could be extracted from the document")
                
                return {
                    "text": text_content.strip(),
                    "metadata": {
                        "format": "doc",
                        "type": "Word 97-2004",
                        "conversion_method": "libreoffice",
                        "original_size": len(content)
                    }
                }
                
            except Exception as e:
                print(f"Error during conversion: {str(e)}")
                print(f"Temp directory contents: {os.listdir(temp_dir) if os.path.exists(temp_dir) else 'directory not found'}")
                raise
            finally:
                # Clean up temporary directory and files
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    print(f"Warning: Failed to clean up temporary directory {temp_dir}: {str(e)}")
                    
        except Exception as e:
            raise ValueError(f"Error processing Word 97-2004 document: {str(e)}")

    @staticmethod
    def _process_text(file: BinaryIO) -> Dict[str, str]:
        """Process text files and extract content."""
        try:
            content = file.read().decode('utf-8')
            return {
                "text": content,
                "metadata": {}
            }
        except Exception as e:
            raise ValueError(f"Error processing text file: {str(e)}")

    @staticmethod
    def get_supported_extensions() -> list:
        """Return list of supported file extensions."""
        return ['pdf', 'doc', 'docx', 'txt', 'md', 'csv'] 