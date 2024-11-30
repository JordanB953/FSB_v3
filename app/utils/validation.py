import os
from typing import List, Tuple
import PyPDF2

class Validator:
    """Handles validation of inputs and files."""
    
    @staticmethod
    def validate_company_info(company_name: str, industry: str, products: str) -> Tuple[bool, str]:
        """
        Validate company information inputs.
        Returns (is_valid, error_message).
        """
        if not company_name or len(company_name) > 100:
            return False, "Company name must be between 1 and 100 characters"
        
        if not industry or len(industry) > 50:
            return False, "Industry must be between 1 and 50 characters"
        
        if not products or len(products) > 200:
            return False, "Products description must be between 1 and 200 characters"
            
        return True, ""

    @staticmethod
    def validate_pdf_files(files: List[object]) -> Tuple[bool, str]:
        """
        Validate uploaded PDF files.
        Returns (is_valid, error_message).
        """
        if not files:
            return False, "No files uploaded"
            
        for file in files:
            try:
                # Check file extension
                if not file.name.lower().endswith('.pdf'):
                    return False, f"File {file.name} is not a PDF"
                
                # Verify PDF is readable
                try:
                    PyPDF2.PdfReader(file)
                    file.seek(0)  # Reset file pointer after reading
                except:
                    return False, f"File {file.name} is not a valid PDF"
                    
            except Exception as e:
                return False, f"Error validating {file.name}: {str(e)}"
                
        return True, ""