import os
from gtts import gTTS

class AudioService:
    """Service for converting text to speech"""
    
    def generate_audio(self, text: str, output_path: str) -> bool:
        """
        Generate an audio file from text using gTTS
        
        Args:
            text: Text content to convert to speech
            output_path: Path where the audio file will be saved
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure the directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Generate audio file using Google Text-to-Speech
            tts = gTTS(text=text, lang='en', slow=False)
            # tts = gTTS(text=text, lang='en', slow=False, tld='co.in') // Uncomment for Indian English accent
            tts.save(output_path)
            
            return True
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return False