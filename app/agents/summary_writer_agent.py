# app/agents/summary_writer_agent.py
import openai
import os
import re
from typing import Dict, List, Any

from dotenv import load_dotenv
load_dotenv()


class SummaryWriterAgent:
    """Agent responsible for generating initial paper summaries"""
    
    def __init__(self):
        # Initialize OpenAI client (assuming API key is set in environment variables)
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def generate_summary(
        self, 
        full_text: str
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive summary of a research paper
        
        Args:
            title: Paper title
            authors: List of paper authors
            abstract: Paper abstract
            full_text: Full text of the paper
            
        Returns:
            Dictionary containing summary sections
        """
        # Prepare prompt for the LLM
        system_prompt = """
        You are a research paper summarization expert. Your task is to create a clear, 
        accurate and comprehensive summary of an academic paper. Focus on:
        
        1. The main findings and contributions
        2. The methodology used
        3. The implications of the research
        4. Important quotes that illustrate key points
        
        Keep the summary concise but thorough. Use language that is accessible while 
        preserving the technical accuracy of the content.
        """
        
        user_prompt = f"""
        Please summarize the following research paper:
        
        
        Paper content:
        {full_text[:5000]}  # Limiting to avoid token limits
        """
        
        # Generate summary using OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",  # or any appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=1500
        )
        
        # Extract summary text
        summary_text = response.choices[0].message.content
        
        # Extract specific sections
        sections = self._extract_sections_from_summary(summary_text)
        
        return sections
        
    def _extract_sections_from_summary(self, summary_text: str) -> Dict[str, Any]:
        """
        Extract structured sections from the generated summary
        
        Args:
            summary_text: Raw summary text from the LLM
            
        Returns:
            Dictionary with structured summary sections
        """
        # Default structure
        result = {
            "summary": summary_text,
            "key_findings": [],
            "methodology": "Not specifically extracted",
            "implications": "Not specifically extracted",
            "citations": []
        }
        
        # Try to extract key findings (often in bullet points)
        findings = []
        lines = summary_text.split('\n')
        
        # Look for bullet points or numbered lists
        in_findings_section = False
        for line in lines:
            line = line.strip()
            
            # Check if we're in a key findings section
            if any(marker in line.lower() for marker in ["key findings", "main findings", "contributions", "results"]):
                in_findings_section = True
                continue
                
            # Check for methodology section
            if any(marker in line.lower() for marker in ["methodology", "methods", "approach"]):
                in_findings_section = False
                
            # Extract bullet points in findings section
            if in_findings_section and (line.startswith('-') or line.startswith('•') or 
                                       (line[0].isdigit() and line[1:3] in ['. ', ') '])):
                findings.append(line.lstrip('-•0123456789.) ').strip())
                
        # If we found explicit findings, use them
        if findings:
            result["key_findings"] = findings
        else:
            # Otherwise, try to extract the first few sentences as key findings
            sentences = re.split(r'(?<=[.!?])\s+', summary_text)
            result["key_findings"] = [s for s in sentences[:3] if len(s) > 20]
            
        # Try to extract methodology section
        methodology_pattern = r'(methodology|methods|approach).*?(?=\n\n|\Z)'
        methodology_match = re.search(methodology_pattern, summary_text, re.IGNORECASE | re.DOTALL)
        if methodology_match:
            result["methodology"] = methodology_match.group(0).strip()
            
        # Try to extract implications section
        implications_pattern = r'(implications|conclusion|impact|significance).*?(?=\n\n|\Z)'
        implications_match = re.search(implications_pattern, summary_text, re.IGNORECASE | re.DOTALL)
        if implications_match:
            result["implications"] = implications_match.group(0).strip()
            
        # Try to extract citations (text in quotes)
        citations_pattern = r'"([^"]+)"'
        citations = re.findall(citations_pattern, summary_text)
        if citations:
            result["citations"] = citations
            
        return result