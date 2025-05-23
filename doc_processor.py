import os
import logging
import fitz  # PyMuPDF for PDFs
import docx

logger = logging.getLogger(__name__)

class DocProcessor:
    def __init__(self, folder_path):
        """
        Initializes the document processor.
        
        :param folder_path: Path to the directory containing documents.
        """
        self.folder_path = folder_path
        if not os.path.exists(folder_path):
            logger.error(f"Folder does not exist: {folder_path}")
            raise FileNotFoundError(f"Folder not found: {folder_path}")

    def _extract_text_from_pdf(self, pdf_path):
        """Extracts text from a PDF file and prefixes each page with a header indicating the page number."""
        try:
            doc = fitz.open(pdf_path)
            texts = []
            for page_no, page in enumerate(doc):
                # Retrieve the page text
                page_text = page.get_text("text")
                # Add a header with the page number
                header = f"PAGE: {page_no + 1}"
                texts.append(f"{header}\n{page_text}")
            # Join pages with extra newline separation
            return "\n\n".join(texts)
        except Exception as e:
            logger.error(f"Error extracting text from PDF {pdf_path}: {e}")
            return ""

    def _extract_text_from_docx(self, docx_path):
        """Extracts text from a DOCX file."""
        try:
            doc = docx.Document(docx_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {docx_path}: {e}")
            return ""

    def process_documents(self):
        """
        Reads all PDFs and DOCX files in the directory and extracts their text.
        
        :return: List of tuples (file_name, extracted_text).
        """
        documents = []
        for file in os.listdir(self.folder_path):
            full_path = os.path.join(self.folder_path, file)
            text = ""

            if file.endswith(".pdf"):
                text = self._extract_text_from_pdf(full_path)
            elif file.endswith(".docx"):
                text = self._extract_text_from_docx(full_path)
            else:
                logger.warning(f"Skipping unsupported file type: {file}")

            if text:
                documents.append((file, text))

        logger.info(f"Processed {len(documents)} documents from {self.folder_path}.")
        return documents
