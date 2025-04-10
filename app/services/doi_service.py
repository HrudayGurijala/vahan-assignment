import requests
from typing import Optional, Dict, Any
from urllib.parse import urlparse


class DoiService:
    """Service for resolving DOI references and retrieving paper details"""
    
    def __init__(self):
        self.crossref_api_url = "https://api.crossref.org/works/"
        self.headers = {
            "User-Agent": "ResearchPaperSummarizer/1.0 (mailto:contact@example.com)"
        }
        
    def get_paper_details(self, doi: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve paper details from a DOI using the CrossRef API
        
        Args:
            doi: Digital Object Identifier for the paper or DOI URL
            
        Returns:
            Dictionary containing paper details or None if not found
        """
        # Clean and extract DOI string
        doi = self._extract_doi(doi.strip())
        if not doi:
            return None
            
        # Make request to CrossRef API
        try:
            response = requests.get(
                f"{self.crossref_api_url}{doi}",
                headers=self.headers,
                timeout=30  # Add timeout for safety
            )
            
            response.raise_for_status()  # Raise exception for non-200 responses
                
            data = response.json()
            message = data.get("message", {})
            
            # Extract relevant information
            result = {
                "title": message.get("title", ["Unknown Title"])[0] if message.get("title") else "Unknown Title",
                "doi": message.get("DOI"),
                "url": message.get("URL"),
                "type": message.get("type"),
                "publisher": message.get("publisher"),
                "publication_date": self._extract_publication_date(message),
                "authors": []
            }
            
            # Extract authors
            for author in message.get("author", []):
                name_parts = []
                if "given" in author:
                    name_parts.append(author["given"])
                if "family" in author:
                    name_parts.append(author["family"])
                    
                if name_parts:
                    result["authors"].append(" ".join(name_parts))
            
            # Try to find PDF URL
            result["pdf_url"] = self._extract_pdf_url(message)
            
            return result
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error retrieving DOI information: {str(e)}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error retrieving DOI information: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"Timeout error retrieving DOI information: {str(e)}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving DOI information: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error processing DOI information: {str(e)}")
            return None
    
    def _extract_doi(self, doi_string: str) -> Optional[str]:
        """
        Extract DOI from a string that might be a DOI or a DOI URL
        
        Args:
            doi_string: String containing a DOI or DOI URL
            
        Returns:
            Clean DOI string or None if invalid
        """
        # Check if it's a URL
        if doi_string.startswith(("http://", "https://")):
            # Handle doi.org URLs
            parsed = urlparse(doi_string)
            if parsed.netloc == "doi.org" or parsed.netloc.endswith(".doi.org"):
                # Extract the path without leading slash
                path = parsed.path.lstrip('/')
                return path
        
        # Handle direct DOI strings (e.g., "10.1000/xyz123")
        if doi_string.startswith("doi:"):
            return doi_string[4:].strip()
            
        return doi_string
    
    def _extract_publication_date(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract publication date from CrossRef message
        
        Args:
            message: CrossRef API message data
            
        Returns:
            Publication date as string or None if not found
        """
        date_parts = message.get("published-print", {}).get("date-parts", [[]])[0]
        if not date_parts and "published-online" in message:
            date_parts = message.get("published-online", {}).get("date-parts", [[]])[0]
        
        if date_parts:
            # Format date based on available parts (year, month, day)
            if len(date_parts) == 3:
                return f"{date_parts[0]}-{date_parts[1]:02d}-{date_parts[2]:02d}"
            elif len(date_parts) == 2:
                return f"{date_parts[0]}-{date_parts[1]:02d}"
            elif len(date_parts) == 1:
                return f"{date_parts[0]}"
        
        return None
            
    def _extract_pdf_url(self, message: Dict[str, Any]) -> Optional[str]:
        """
        Extract PDF URL from CrossRef message data if available
        
        Args:
            message: CrossRef API message data
            
        Returns:
            URL to PDF if found, otherwise None
        """
        # Check for direct link in the link section
        for link in message.get("link", []):
            if link.get("content-type") == "application/pdf":
                return link.get("URL")
        
        # Check for links with "application/pdf" in content-type
        if "link" in message:
            for link in message.get("link", []):
                if link.get("content-type", "").startswith("application/pdf"):
                    return link.get("URL")
        
        # Check for resource links
        if "resource" in message and "primary" in message["resource"]:
            primary = message["resource"]["primary"]
            if "URL" in primary:
                for url in primary["URL"]:
                    if url.lower().endswith(".pdf"):
                        return url
        
        # If we still don't have a PDF URL, return the main URL
        return message.get("URL")