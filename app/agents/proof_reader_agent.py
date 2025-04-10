import openai
import os
from typing import Dict, List, Any

from dotenv import load_dotenv
load_dotenv()


class ProofReaderAgent:
    """Agent responsible for reviewing and improving paper summaries"""
    
    def __init__(self):
        # Initialize OpenAI client (assuming API key is set in environment variables)
        self.client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
    def review_summary(
        self, 
        draft_summary: Dict[str, Any],
        full_text: str
    ) -> Dict[str, Any]:
        """
        Review and improve a draft summary to make it brief and precise
        
        Args:
            draft_summary: Draft summary generated by the SummaryWriterAgent
            full_text: Full text of the paper
            
        Returns:
            Improved summary dictionary with plain text only
        """
        # Prepare prompt for the LLM
        system_prompt = """
        You are an expert academic editor specializing in research paper summaries. 
        Your task is to review and improve a draft summary of an academic paper.
        
        1. Make the summary brief and focusing on the main findings and methodologies
        2. Ensure ALL methodologies mentioned in the paper are included
        3. Capture the key ideas accurately
        4. Use plain text ONLY - no markdown, no bullet points, no formatting
        
        Provide a concise, plain text summary that researchers can quickly read to understand the paper's core contributions and methods.
        """
        
        user_prompt = f"""
        Please review this draft summary and create a brief, precise plain text summary of the paper:
        
        Draft Summary:
        {draft_summary.get('summary', '')}
        
        Key Findings:
        {', '.join(draft_summary.get('key_findings', []))}
        
        Methodology:
        {draft_summary.get('methodology', '')}
        
        Important: 
        1. Focus especially on capturing ALL methodologies and key ideas from the paper
        2. The final output should be PLAIN TEXT ONLY, with no markdown or bullet points
        3. Keep it brief but comprehensive (3-4 paragraphs maximum)
        4. Make sure the language is clear and direct
        
        First few paragraphs of the paper:
        {full_text[:5000]}
        """
        
        # Generate improved summary using OpenAI API
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        # Extract improved summary text - plain text only
        improved_summary_text = response.choices[0].message.content
        
        # Clean up any markdown that might have been included despite instructions
        # improved_summary_text = self._clean_markdown(improved_summary_text)
        
        # Prepare the result - keeping everything in the main summary text
        result = {
            "summary": improved_summary_text,
            "key_findings": draft_summary.get("key_findings", []),
            "methodology": "Included in summary",
            "implications": "Included in summary",
            "citations": []
        }
        
        return result
    
    # def _clean_markdown(self, text: str) -> str:
    #     """
    #     Remove markdown formatting from text
        
    #     Args:
    #         text: Text that might contain markdown
            
    #     Returns:
    #         Clean plain text
    #     """
    #     # Remove headers (# Header)
    #     text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
        
    #     # Remove bold/italic markers
    #     text = re.sub(r'\*\*|\*|__|\^|_', '', text)
        
    #     # Remove bullet points
    #     text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
        
    #     # Remove numbered lists (convert "1. " to just the text)
    #     text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
    #     # Remove blockquotes
    #     text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
        
    #     # Remove horizontal rules
    #     text = re.sub(r'^\s*[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
        
    #     # Remove code blocks
    #     text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        
    #     # Remove inline code
    #     text = re.sub(r'`([^`]+)`', r'\1', text)
        
    #     # Remove extra whitespace
    #     text = re.sub(r'\n\s*\n+', '\n\n', text)
        
    #     return text.strip()