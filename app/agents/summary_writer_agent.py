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
        Generate a brief, precise summary of a research paper
        
        Args:
            full_text: Full text of the paper
            
        Returns:
            Dictionary containing summary sections
        """
        # Prepare prompt for the LLM
        system_prompt = """
        You are a research paper summarization expert. Your task is to create a brief, 
        precise summary of an academic paper focusing on:
        
        1. The main findings and contributions
        2. ALL methodologies used (be specific and comprehensive about methods)
        3. The key ideas presented in the paper
        4. The implications of the research
        
        Keep the summary concise (about 3-4 paragraphs maximum). Use plain text format only.
        Do not use markdown formatting, lists, bullets, or headers in your response.
        """
        
        user_prompt = f"""
        Please create a brief, precise summary of the following research paper, focusing specifically on capturing ALL methodologies and key ideas mentioned:
        
        Paper content:
        {full_text[:5000]}  # Limiting to avoid token limits
        
        Important: Provide your response as plain text only, without any markdown formatting, lists, or bullet points.
        """
        
        # Generate summary using OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",  # or any appropriate model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lower temperature for more focused output
            max_tokens=1000
        )
        
        # Extract summary text
        summary_text = response.choices[0].message.content
        
        # Extract specific sections using a more robust method
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
        # Default structure - focusing just on what we need
        result = {
            "summary": summary_text,
            "key_findings": [],
            "methodology": "Included in summary",
            "implications": "Included in summary",
            "citations": []
        }
        
        # Extract key findings (sentences that contain key indicators)
        key_finding_indicators = [
            "find", "show", "reveal", "demonstrate", "conclude", 
            "suggest", "indicate", "highlight", "discover"
        ]
        
        sentences = re.split(r'(?<=[.!?])\s+', summary_text)
        findings = []
        
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in key_finding_indicators):
                if len(sentence) > 15:  # Avoid very short fragments
                    findings.append(sentence.strip())
        
        # If we found findings, use them (limit to 3 for brevity)
        if findings:
            result["key_findings"] = findings[:3]
        else:
            # Otherwise, use the first 2 sentences as key findings
            result["key_findings"] = [s.strip() for s in sentences[:2] if len(s) > 15]
            
        # Try to extract methodology from sentences mentioning methods
        methodology_sentences = []
        for sentence in sentences:
            if any(term in sentence.lower() for term in ["method", "approach", "technique", "procedure", "algorithm", "model"]):
                methodology_sentences.append(sentence.strip())
                
        if methodology_sentences:
            result["methodology"] = " ".join(methodology_sentences)
        
        # Extract implications from sentences mentioning implications
        implication_sentences = []
        for sentence in sentences:
            if any(term in sentence.lower() for term in ["implication", "impact", "result", "outcome", "conclusion"]):
                implication_sentences.append(sentence.strip())
                
        if implication_sentences:
            result["implications"] = " ".join(implication_sentences)
            
        # Extract quotes if any (usually rare in plain text summaries)
        citations_pattern = r'"([^"]+)"'
        citations = re.findall(citations_pattern, summary_text)
        if citations:
            result["citations"] = citations
            
        return result