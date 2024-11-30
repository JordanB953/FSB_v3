import pandas as pd
import PyPDF2
from typing import Dict, Optional
from pathlib import Path
import logging
from datetime import datetime
from app.processors.pdf_redactor import PDFRedactor
from app.utils.debug_config import DebugConfig
from app.processors.pdf_converter import PDFConverter

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handles the extraction and processing of data from PDF bank statements."""
    
    def __init__(self):
        """Initialize the PDF processor with debug configuration."""
        self.debug_config = DebugConfig()
        self.redactor = PDFRedactor()
        self.converter = PDFConverter()
        logger.info("PDFProcessor initialized with debug configuration")
        
    def process_pdf(self, pdf_file, user_email: str, company_name: str) -> Optional[Dict]:
        """
        Process PDF file: redact sensitive info and extract transaction data.
        
        Args:
            pdf_file: Streamlit uploaded file object
            user_email: Email of current user
            company_name: Name of the company
            
        Returns:
            Dictionary containing:
            - transactions_df: Processed DataFrame
            - redaction_stats: Statistics about redaction
            - redacted_pdf_path: Path to redacted PDF
        """
        try:
            logger.info(f"Starting PDF processing for file: {pdf_file.name}")
            
            # First, redact sensitive information
            redacted_pdf_path, redaction_stats = self.redactor.redact_pdf(
                pdf_file, 
                user_email
            )
            
            if not redacted_pdf_path:
                logger.error("PDF redaction failed")
                return None
                
            logger.info(f"PDF redacted successfully: {redacted_pdf_path}")
            
            # Convert PDF to transactions using BSC API
            transactions, error = self.converter.convert_pdf_to_transactions(
                Path(redacted_pdf_path),
                company_name
            )
            
            if error:
                logger.error(f"PDF conversion failed: {error}")
                return None
            
            if not transactions:
                logger.warning("No transactions found in PDF")
                return None
            
            # Convert transactions list to DataFrame
            df = pd.DataFrame(transactions)
            
            # Ensure required columns exist and are properly named
            required_cols = {
                'date': 'date',
                'description': 'description',
                'amount': 'amount'
            }
            
            # Rename columns if needed
            df = df.rename(columns={
                col: required_cols[col.lower()]
                for col in df.columns
                if col.lower() in required_cols
            })
            
            # Convert data types
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
            df['amount'] = pd.to_numeric(df['amount'])
            
                       
            # Verify all required columns exist
            required_cols = {
                'date': 'date',
                'description': 'description',
                'amount': 'amount'
            }
            
            # Rename columns if needed
            df = df.rename(columns={
                col: required_cols[col.lower()]
                for col in df.columns
                if col.lower() in required_cols
            })
            
            # Convert data types
            df['date'] = pd.to_datetime(df['date'], format='%m/%d/%Y')
            df['amount'] = pd.to_numeric(df['amount'])
            
            # Verify all required columns exist
            missing_cols = set(required_cols.values()) - set(df.columns)
            if missing_cols:
                logger.error(f"Missing required columns: {missing_cols}")
                return None
            
            logger.info(f"Processed {len(df)} transactions with columns: {df.columns.tolist()}")
            
            return {
                'transactions_df': df,
                'redaction_stats': redaction_stats,
                'redacted_pdf_path': redacted_pdf_path
            }
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
            return None