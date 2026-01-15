"""
Universal Document Loader.
Automatically detects and extracts text from various file types.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

# File type mappings
SUPPORTED_EXTENSIONS = {
    # Documents
    ".txt": "text",
    ".md": "markdown",
    ".pdf": "pdf",
    ".docx": "docx",
    ".doc": "docx",  # Legacy Word format (requires conversion or text extraction)
    # Structured data
    ".json": "json",
    ".csv": "csv",
    ".xlsx": "excel",
    ".xls": "excel",  # Legacy Excel format
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    # Web
    ".html": "html",
    ".htm": "html",
    # Code
    ".py": "code",
    ".js": "code",
    ".ts": "code",
    ".jsx": "code",
    ".tsx": "code",
    ".java": "code",
    ".cpp": "code",
    ".c": "code",
    ".h": "code",
    ".rs": "code",
    ".go": "code",
    ".rb": "code",
    ".php": "code",
    ".swift": "code",
    ".kt": "code",
    ".sql": "code",
    ".sh": "code",
    ".bash": "code",
    ".css": "code",
    ".scss": "code",
    ".less": "code",
    ".vue": "code",
    ".svelte": "code",
    ".r": "code",
    ".scala": "code",
    ".lua": "code",
    ".perl": "code",
    ".pl": "code",
    # Images (OCR)
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".gif": "image",
    ".bmp": "image",
    ".tiff": "image",
    ".webp": "image",
    # Audio
    ".mp3": "audio",
    ".wav": "audio",
    ".m4a": "audio",
    ".flac": "audio",
    ".ogg": "audio",
    ".aac": "audio",
    ".wma": "audio",
}


def get_file_type(file_path: str) -> Optional[str]:
    """Get the file type category from extension."""
    ext = Path(file_path).suffix.lower()
    return SUPPORTED_EXTENSIONS.get(ext)


def load_text(file_path: str) -> str:
    """Load plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_markdown(file_path: str) -> str:
    """Load markdown file (treated as text)."""
    return load_text(file_path)


def load_pdf(file_path: str) -> str:
    """Load PDF file using pypdf, with OCR fallback for scanned docs."""
    from pypdf import PdfReader
    
    text_parts = []
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    except Exception as e:
        print(f"Error reading PDF text natively: {e}")

    extracted_text = "\n\n".join(text_parts)
    
    # If text is minimal (e.g. scanned), try OCR
    if len(extracted_text.strip()) < 100:
        print(f"PDF {os.path.basename(file_path)} appears scanned (text len < 100). Attempting OCR...")
        try:
            from pdf2image import convert_from_path
            import pytesseract
            
            # Check availability
            try:
                pytesseract.get_tesseract_version()
            except:
                print("Tesseract not installed. Skipping OCR.")
                return extracted_text

            images = convert_from_path(file_path)
            ocr_parts = []
            for i, img in enumerate(images):
                print(f"OCR processing page {i+1}/{len(images)}...")
                text = pytesseract.image_to_string(img)
                ocr_parts.append(text)
            
            return "\n\n".join(ocr_parts)
            
        except ImportError:
            print("pdf2image or pytesseract missing. Install them for OCR support.")
        except Exception as e:
            print(f"OCR failed for PDF: {e}")
            
    return extracted_text


def load_docx(file_path: str) -> str:
    """Load Word document using python-docx."""
    try:
        import docx
        doc = docx.Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)
    except ImportError:
        raise ImportError("python-docx is required for .docx files: pip install python-docx")


def load_json(file_path: str) -> str:
    """Load JSON file and convert to readable text."""
    import json
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Convert to readable text representation
    return json.dumps(data, indent=2, ensure_ascii=False)


def load_csv(file_path: str) -> str:
    """Load CSV file and convert to readable text."""
    try:
        import pandas as pd
        df = pd.read_csv(file_path)
        
        # Convert to markdown table format for better readability
        lines = []
        lines.append("| " + " | ".join(df.columns) + " |")
        lines.append("| " + " | ".join(["---"] * len(df.columns)) + " |")
        
        for _, row in df.iterrows():
            lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
        
        return "\n".join(lines)
    except ImportError:
        raise ImportError("pandas is required for .csv files: pip install pandas")


def load_excel(file_path: str) -> str:
    """Load Excel file and convert to readable text."""
    try:
        import pandas as pd
        
        # Read all sheets
        xl = pd.ExcelFile(file_path)
        all_text = []
        
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(xl, sheet_name=sheet_name)
            all_text.append(f"## Sheet: {sheet_name}\n")
            
            # Convert to markdown table
            lines = []
            lines.append("| " + " | ".join(str(c) for c in df.columns) + " |")
            lines.append("| " + " | ".join(["---"] * len(df.columns)) + " |")
            
            for _, row in df.iterrows():
                lines.append("| " + " | ".join(str(v) for v in row.values) + " |")
            
            all_text.append("\n".join(lines))
        
        return "\n\n".join(all_text)
    except ImportError:
        raise ImportError("pandas and openpyxl are required for .xlsx files: pip install pandas openpyxl")


def load_yaml(file_path: str) -> str:
    """Load YAML file and convert to readable text."""
    try:
        import yaml
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return yaml.dump(data, default_flow_style=False, allow_unicode=True)
    except ImportError:
        raise ImportError("PyYAML is required for .yaml files: pip install pyyaml")


def load_html(file_path: str) -> str:
    """Load HTML file and extract text content."""
    try:
        from bs4 import BeautifulSoup
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            soup = BeautifulSoup(f, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        raise ImportError("beautifulsoup4 is required for .html files: pip install beautifulsoup4")



def load_url(url: str) -> str:
    """Load content from a URL."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        
        # Handle GitHub URLs locally to get raw content
        if "github.com" in url and "/blob/" in url:
            # Convert https://github.com/user/repo/blob/branch/file.py
            # to https://raw.githubusercontent.com/user/repo/branch/file.py
            url = url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        
        # Add user-agent to avoid 403s
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        with httpx.Client(follow_redirects=True, verify=False, timeout=30.0) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
        # If it's a raw code file (from GitHub or otherwise), return text directly
        if "raw.githubusercontent.com" in url or not response.headers.get("content-type", "").startswith("text/html"):
            return response.text
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "iframe"]):
            script.decompose()
            
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        raise Exception(f"Failed to load URL {url}: {e}")

def load_xml(file_path: str) -> str:
    """Load XML file and convert to readable text."""
    try:
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        def extract_text(element, depth=0):
            """Recursively extract text from XML elements."""
            lines = []
            tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag  # Remove namespace
            
            # Add element with text
            if element.text and element.text.strip():
                lines.append(f"{'  ' * depth}{tag}: {element.text.strip()}")
            elif len(element) == 0:
                lines.append(f"{'  ' * depth}{tag}")
            
            # Process children
            for child in element:
                lines.extend(extract_text(child, depth + 1))
            
            # Add tail text
            if element.tail and element.tail.strip():
                lines.append(f"{'  ' * depth}{element.tail.strip()}")
            
            return lines
        
        return "\n".join(extract_text(root))
    except Exception as e:
        # Fallback to raw text if parsing fails
        return load_text(file_path)


def load_code(file_path: str) -> str:
    """Load source code file with language header."""
    ext = Path(file_path).suffix.lower()
    language_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".rs": "rust",
        ".go": "go",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".css": "css",
        ".scss": "scss",
        ".less": "less",
        ".vue": "vue",
        ".svelte": "svelte",
        ".r": "r",
        ".scala": "scala",
        ".lua": "lua",
        ".perl": "perl",
        ".pl": "perl",
    }
    
    language = language_map.get(ext, "code")
    content = load_text(file_path)
    
    # Wrap in code block for clarity
    return f"```{language}\n{content}\n```"


def load_image_ocr(file_path: str) -> str:
    """Load image and extract text using OCR."""
    try:
        from PIL import Image
        
        # First check if tesseract is available
        try:
            import pytesseract
            # Test if tesseract binary is accessible
            pytesseract.get_tesseract_version()
        except Exception:
            # Tesseract not installed - return image info instead of failing
            image = Image.open(file_path)
            width, height = image.size
            return f"[Image file: {Path(file_path).name}]\nDimensions: {width}x{height} pixels\nFormat: {image.format}\nMode: {image.mode}\n\nNote: OCR not available - install tesseract-ocr to extract text from images."
        
        # Tesseract is available, proceed with OCR
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        
        if text.strip():
            return text.strip()
        else:
            # No text found in image
            width, height = image.size
            return f"[Image file: {Path(file_path).name}]\nDimensions: {width}x{height} pixels\nNo text detected in image."
            
    except ImportError:
        raise ImportError("Pillow is required for image processing: pip install pillow")


def load_document(file_path: str) -> Dict[str, Any]:
    """
    Universal document loader.
    Automatically detects file type and extracts text.
    
    Returns:
        Dict with 'text', 'file_type', 'success', and optional 'error'
    """
    file_type = get_file_type(file_path)
    
    if file_type is None:
        return {
            "text": "",
            "file_type": "unknown",
            "success": False,
            "error": f"Unsupported file type: {Path(file_path).suffix}"
        }
    
    loaders = {
        "text": load_text,
        "markdown": load_markdown,
        "pdf": load_pdf,
        "docx": load_docx,
        "json": load_json,
        "csv": load_csv,
        "excel": load_excel,
        "yaml": load_yaml,
        "xml": load_xml,
        "html": load_html,
        "code": load_code,
        "image": load_image_ocr,
    }
    
    # Audio is handled separately by the transcription pipeline
    if file_type == "audio":
        return {
            "text": "",
            "file_type": "audio",
            "success": True,
            "requires_transcription": True
        }
    
    loader = loaders.get(file_type)
    if loader is None:
        return {
            "text": "",
            "file_type": file_type,
            "success": False,
            "error": f"No loader available for type: {file_type}"
        }
    
    try:
        text = loader(file_path)
        return {
            "text": text,
            "file_type": file_type,
            "success": True,
            "char_count": len(text)
        }
    except Exception as e:
        return {
            "text": "",
            "file_type": file_type,
            "success": False,
            "error": str(e)
        }


def load_directory(directory_path: str, recursive: bool = True) -> list:
    """
    Load all supported documents from a directory.
    
    Args:
        directory_path: Path to the directory
        recursive: Whether to include subdirectories
    
    Returns:
        List of dicts with document info and extracted text
    """
    documents = []
    path = Path(directory_path)
    
    if recursive:
        files = path.rglob("*")
    else:
        files = path.glob("*")
    
    for file_path in files:
        if file_path.is_file():
            file_type = get_file_type(str(file_path))
            if file_type:
                result = load_document(str(file_path))
                result["file_path"] = str(file_path)
                result["file_name"] = file_path.name
                documents.append(result)
    
    return documents


def download_youtube_audio(url: str, output_dir: str = "uploads") -> str:
    """
    Download audio from YouTube video URL using yt-dlp.
    Returns absolute path to the downloaded MP3 file.
    """
    try:
        import yt_dlp
        import uuid
        import os
        
        # Ensure upload dir exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate unique ID
        file_id = str(uuid.uuid4())
        # Template for yt-dlp (it appends extension)
        output_template = os.path.join(output_dir, f"{file_id}.%(ext)s")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': True,
            'no_warnings': True,
        }
        
        print(f"Downloading YouTube audio from {url}...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # The file should be at {file_id}.mp3
        final_path = os.path.join(output_dir, f"{file_id}.mp3")
        
        if os.path.exists(final_path):
            return final_path
            
        raise FileNotFoundError(f"Expected audio file not found at {final_path}")
        
    except ImportError:
        raise ImportError("yt-dlp is required: pip install yt-dlp")
    except Exception as e:
        raise Exception(f"YouTube download failed: {str(e)}")
