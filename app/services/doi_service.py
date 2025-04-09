# app/services/doi_service.py
import requests
from typing import Optional, Dict, Any

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
            doi: Digital Object Identifier for the paper
            
        Returns:
            Dictionary containing paper details or None if not found
        """
        # Clean DOI string
        doi = doi.strip()
        
        # Make request to CrossRef API
        try:
            response = requests.get(
                f"{self.crossref_api_url}{doi}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            message = data.get("message", {})
            
            # Extract relevant information
            result = {
                "title": message.get("title", ["Unknown Title"])[0],
                "doi": message.get("DOI"),
                "url": message.get("URL"),
                "type": message.get("type"),
                "publisher": message.get("publisher"),
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
            
        except Exception as e:
            print(f"Error retrieving DOI information: {str(e)}")
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
                
        # Check for resource links
        for resource in message.get("resource", {}).get("primary", {}).get("URL", []):
            if resource.lower().endswith(".pdf"):
                return resource
                
        # If we still don't have a PDF URL, return the main URL
        return message.get("URL")