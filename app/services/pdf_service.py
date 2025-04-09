from datetime import datetime
import PyPDF2
from typing import Dict, Any, Optional
import requests
import os
import io


class PdfService:
    """Service for processing PDF files and extracting text and metadata"""

    def extract_text(self, file_path: str) -> str:
        """
        Extract text content from a PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Extracted text content as a string
        """
        text = ""
        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text() + "\n\n"

            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""

    def extract_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file

        Args:
            file_path: Path to the PDF file

        Returns:
            Dictionary containing metadata fields
        """
        metadata = {
            "title": "Unknown Title",
            "authors": [],
            "abstract": "",
            "publication_date": None,
        }

        def parse_date(date_str: str) -> Optional[datetime]:
            """
            Parse date string from PDF metadata.

            Args:
                date_str: The date string to parse.

            Returns:
                A datetime object if parsing is successful, otherwise None.
            """
            try:
                # Handle standard PDF date format (D:%Y%m%d%H%M%S%z)
                if date_str.startswith("D:"):
                    return datetime.strptime(date_str[2:], "%Y%m%d%H%M%S%z")
                # Handle ISO 8601 format (e.g., 2020-04-28 00:26:23+00:00)
                return datetime.fromisoformat(date_str)
            except ValueError as e:
                print(f"Error parsing date '{date_str}': {e}")
                return None

        try:
            with open(file_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                info = reader.metadata

                if info:
                    # Extract title
                    if info.title:
                        metadata["title"] = info.title

                    # Extract author(s)
                    if info.author:
                        if isinstance(info.author, str):
                            authors = info.author.split(", ")
                            metadata["authors"] = [a.strip() for a in authors]
                        else:
                            metadata["authors"] = [info.author]

                    # Extract creation date
                    if info.creation_date:
                        metadata["publication_date"] = parse_date(str(info.creation_date))

                # Try to extract abstract from first page text
                first_page_text = reader.pages[0].extract_text()
                abstract = self._extract_abstract(first_page_text)
                if abstract:
                    metadata["abstract"] = abstract

            return metadata

        except Exception as e:
            print(f"Error extracting metadata from PDF: {str(e)}")
            return metadata

    def _extract_abstract(self, text: str) -> Optional[str]:
        """
        Attempt to extract the abstract from paper text

        Args:
            text: Text content from the paper

        Returns:
            Abstract text if found, otherwise None
        """
        # Common abstract markers
        abstract_start_markers = ["Abstract", "ABSTRACT", "Summary", "SUMMARY"]
        abstract_end_markers = ["Introduction", "INTRODUCTION", "Keywords", "KEYWORDS"]

        abstract = None

        # Try to find abstract section
        for start_marker in abstract_start_markers:
            if start_marker in text:
                start_idx = text.find(start_marker) + len(start_marker)

                # Find the end of the abstract
                end_idx = len(text)
                for end_marker in abstract_end_markers:
                    marker_idx = text.find(end_marker, start_idx)
                    if marker_idx > 0 and marker_idx < end_idx:
                        end_idx = marker_idx

                # Extract the abstract
                abstract = text[start_idx:end_idx].strip()
                break

        return abstract
    
    def download_pdf(self, url: str, output_path: str) -> bool:
        """
        Download a PDF from a URL and save it to the specified path
        
        Args:
            url: URL of the PDF to download
            output_path: Path where the PDF should be saved
            
        Returns:
            True if download was successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Send HTTP request with timeout
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # Raise an exception for error status codes
            
            # Check if content is likely a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'application/pdf' not in content_type and not url.lower().endswith('.pdf'):
                # If URL doesn't end with .pdf and content-type isn't PDF, try to validate content
                try:
                    # Try to read it as a PDF to validate
                    PyPDF2.PdfReader(io.BytesIO(response.content))
                except:
                    raise ValueError("Downloaded content does not appear to be a valid PDF")
            
            # Save the PDF
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            return True
        except Exception as e:
            print(f"Error downloading PDF from {url}: {str(e)}")
            raise e  # Re-raise the exception to be caught by the caller
