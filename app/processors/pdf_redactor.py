import fitz  # PyMuPDF
import re  
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from app.utils.debug_config import DebugConfig

logger = logging.getLogger(__name__)

class PDFRedactor:
    """Handles redaction of sensitive information from PDF files."""
    
    def __init__(self):
        self.debug_config = DebugConfig()
        self.patterns = {
            'account_numbers': r'(?<!\d/)\b\d[\d\s-]{8,15}\d\b(?!\d/)',
            'addresses': r'[A-Z][A-Za-z\s]+?\s[A-Z]{2}\s\d{5}'
        }
    
    def redact_pdf(self, pdf_file, user_email: str) -> Tuple[Optional[str], Dict]:
        stats = {
            'account_numbers': 0,
            'names': 0,
            'addresses': 0,
            'processing_time': 0,
            'success': False
        }
        
        try:
            start_time = datetime.now()
            
            # Create user-specific directory
            user_dir = self.debug_config.pdfs_dir / user_email.replace('@', '_at_')
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate output filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_name = Path(pdf_file.name).stem
            output_filename = f"{original_name}_redacted_{timestamp}.pdf"
            output_path = user_dir / output_filename
            
            # Process PDF using PyMuPDF
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            logger.debug(f"Processing PDF {pdf_file.name} with {len(doc)} pages")
            
            # Process first page for addresses
            first_page = doc[0]
            text = first_page.get_text("text")
            
            # Find and redact addresses
            address_matches = re.finditer(self.patterns['addresses'], text)
            for match in address_matches:
                text_areas = first_page.search_for(match.group())
                for rect in text_areas:
                    first_page.add_redact_annot(rect)
                    stats['addresses'] += 1
            
            # Process account numbers on all pages
            for page in doc:
                text = page.get_text("text")
                matches = list(re.finditer(self.patterns['account_numbers'], text))
                for match in matches:
                    matched_text = match.group()
                    # Double check it's not a date format
                    if '/' not in matched_text:
                        text_areas = page.search_for(matched_text)
                        for rect in text_areas:
                            page.add_redact_annot(rect)
                            stats['account_numbers'] += 1
                
                page.apply_redactions()
            
            # Save the redacted PDF
            doc.save(str(output_path))
            doc.close()
            
            stats['processing_time'] = (datetime.now() - start_time).total_seconds()
            stats['success'] = True
            
            logger.info(f"PDF redacted successfully: {output_path}")
            logger.info(f"Redaction stats: {stats}")
            
            return str(output_path), stats
            
        except Exception as e:
            logger.error(f"Error redacting PDF: {str(e)}", exc_info=True)
            return None, stats