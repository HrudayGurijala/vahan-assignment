# app/services/arxiv_service.py
import arxiv
from datetime import datetime
from typing import List, Optional, Dict, Any

class ArxivService:
    """Service for interacting with the arXiv API to search and retrieve papers"""
    
    def search(
        self, 
        query: str, 
        max_results: int = 10, 
        sort_by: str = "relevance",
        sort_order: str = "descending",
        year_from: Optional[int] = None,
        year_to: Optional[int] = None
    ) -> List[Any]:
        """
        Search for papers on arXiv based on provided parameters
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            sort_by: Sort method (relevance, lastUpdatedDate, submittedDate)
            sort_order: Sort order (ascending or descending)
            year_from: Filter papers published from this year
            year_to: Filter papers published until this year
            
        Returns:
            List of arXiv paper objects
        """
        # Build date filter if years are provided
        date_filter = ""
        if year_from:
            date_filter += f" AND submittedDate:[{year_from}0101 TO "
            date_filter += f"{year_to}1231]" if year_to else "99991231]"
        elif year_to:
            date_filter += f" AND submittedDate:[00010101 TO {year_to}1231]"
            
        # Combine with main query
        full_query = query + date_filter
        
        # Map sort parameters to arXiv API options
        sort_options = {
            "relevance": arxiv.SortCriterion.Relevance,
            "lastUpdatedDate": arxiv.SortCriterion.LastUpdatedDate,
            "submittedDate": arxiv.SortCriterion.SubmittedDate
        }
        
        sort_order_options = {
            "ascending": arxiv.SortOrder.Ascending,
            "descending": arxiv.SortOrder.Descending
        }
        
        # Create client and search
        client = arxiv.Client()
        search = arxiv.Search(
            query=full_query,
            max_results=max_results,
            sort_by=sort_options.get(sort_by, arxiv.SortCriterion.Relevance),
            sort_order=sort_order_options.get(sort_order, arxiv.SortOrder.Descending)
        )
        
        # Execute search and return results
        results = list(client.results(search))
        return results
        
    def get_paper_by_id(self, arxiv_id: str) -> Any:
        """
        Retrieve a specific paper by its arXiv ID
        
        Args:
            arxiv_id: The arXiv identifier
            
        Returns:
            arXiv paper object
        """
        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        results = list(client.results(search))
        
        if not results:
            return None
        
        return results[0]