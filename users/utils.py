import os
import re
import io
import PyPDF2
import openai
from django.conf import settings

# Configure Azure OpenAI API
openai.api_type = "azure"
openai.api_key = settings.AZURE_OPENAI_API_KEY
openai.api_base = settings.AZURE_OPENAI_ENDPOINT
openai.api_version = settings.AZURE_OPENAI_API_VERSION

def extract_text_from_pdf(file):
    """
    Extract text from a PDF file.
    
    Args:
        file: An uploaded file object
        
    Returns:
        str: Extracted text from the PDF
    """
    try:
        # Create a PDF reader object using PyPDF2
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
        
        # Get the total number of pages
        num_pages = len(pdf_reader.pages)
        
        # Extract text from all pages (limit to first 20 pages for large PDFs)
        max_pages = min(num_pages, 20)
        text = ""
        
        for page_num in range(max_pages):
            page = pdf_reader.pages[page_num]
            text += page.extract_text() + "\n\n"
        
        # Reset file pointer
        file.seek(0)
        
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

def extract_metadata_with_openai(text, filename):
    """
    Use Azure OpenAI to extract metadata from PDF text.
    
    Args:
        text (str): The extracted text from the PDF
        filename (str): Original filename for reference
        
    Returns:
        dict: Extracted metadata including title, authors, etc.
    """
    # Default metadata
    default_metadata = {
        "title": os.path.splitext(filename)[0].replace("_", " "),
        "authors": [],
        "year": None,
        "conference": None,
        "abstract": "",
        "field": "Computer Science",
        "keywords": [],
        "doi": None,
        "bibtex": None,
        "sourceCode": None
    }
    
    if not text or len(text.strip()) < 50:
        return default_metadata
    
    # Prepare a sample of the text (first 10000 characters should be enough)
    text_sample = text[:10000]
    
    try:
        # Create the prompt for OpenAI
        prompt = f"""
Extract the following metadata from this research paper:
1. Title
2. Authors (as a list)
3. Year of publication
4. Conference or journal name
5. Abstract
6. Research field (e.g., Computer Vision, NLP, etc.)
7. Keywords (as a list)
8. DOI (if present)
9. Generate a BibTeX citation
10. Source code URL (look for GitHub links or other repository URLs in the paper)

The filename is: {filename}

Here's the beginning of the paper:
{text_sample}

Respond in the following JSON format only, without any additional text or explanation:
{{
  "title": "Paper Title",
  "authors": ["Author 1", "Author 2"],
  "year": YYYY,
  "conference": "Conference Name",
  "abstract": "Abstract text...",
  "field": "Research Field",
  "keywords": ["keyword1", "keyword2"],
  "doi": "DOI string or null",
  "bibtex": "Complete BibTeX entry or null",
  "sourceCode": "URL to source code repository or null"
}}
"""

        # Call Azure OpenAI API
        response = openai.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,  # Use the Azure deployment name
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1000
        )
        
        # Extract the response content
        result = response.choices[0].message.content.strip()
        
        # Find JSON in the response
        json_match = re.search(r'({[\s\S]*})', result)
        if json_match:
            result = json_match.group(1)
        
        # Parse JSON
        import json
        metadata = json.loads(result)
        
        # Validate and fill in any missing fields with defaults
        for key, default_value in default_metadata.items():
            if key not in metadata or metadata[key] is None:
                metadata[key] = default_value
        
        return metadata
        
    except Exception as e:
        print(f"Error extracting metadata with Azure OpenAI: {e}")
        return default_metadata 