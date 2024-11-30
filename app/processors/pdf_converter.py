import requests
import os
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from app.utils.debug_config import DebugConfig
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFConverter:
    """Handles conversion of PDFs to transaction data using Bank Statement Converter API."""
    
    def __init__(self):
        """Initialize converter with API configuration."""
        self.debug_config = DebugConfig()
        self.api_key = os.getenv('BSC_API_KEY')
        if not self.api_key:
            raise ValueError("BSC_API_KEY not found in environment variables")
        
        self.api_base_url = 'https://api2.bankstatementconverter.com/api/v1'
        
    def _standardize_date(self, date_str: str) -> str:
        """
        Standardize date string to MM/DD/YYYY format.
        
        Handles formats:
        - MM/DD
        - MM/DD/YY
        - MM/DD/YYYY
        """
        try:
            parts = date_str.split('/')
            if len(parts) == 2:  # MM/DD
                month, day = parts
                year = datetime.now().year
            elif len(parts) == 3:  # MM/DD/YY or MM/DD/YYYY
                month, day, year = parts
                if len(year) == 2:  # YY format
                    year = f"20{year}"  # Assume 20xx for two-digit years
            else:
                logger.warning(f"Unexpected date format: {date_str}")
                return date_str
            
            return f"{month}/{day}/{year}"
            
        except Exception as e:
            logger.warning(f"Error standardizing date {date_str}: {str(e)}")
            return date_str

    def convert_pdf_to_transactions(self, pdf_path: Path, company_name: str) -> Tuple[Optional[List[Dict]], str]:
        """
        Convert PDF to transaction data using BSC API.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Tuple of (transactions list or None, error message)
        """
        try:
            # Create company output directory
            company_dir = Path("bsc_output") / f"{company_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}"
            company_dir.mkdir(parents=True, exist_ok=True)
            
            # Convert string path to Path object if needed
            pdf_path = Path(pdf_path) if isinstance(pdf_path, str) else pdf_path
            
            # Step 1: Upload PDF
            upload_url = f"{self.api_base_url}/BankStatement"
            headers = {"Authorization": self.api_key}
            
            with open(pdf_path, "rb") as file:
                files = {"file": (pdf_path.name, file)}
                response = requests.post(upload_url, headers=headers, files=files)
            
            if response.status_code != 200:
                return None, f"Upload failed: {response.text}"
                
            uuid = response.json()[0]["uuid"]
            
            # Step 2: Convert to JSON
            convert_url = f"{self.api_base_url}/BankStatement/convert?format=JSON"
            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json"
            }
            data = json.dumps([uuid])
            
            response = requests.post(convert_url, headers=headers, data=data)
            
            if response.status_code != 200:
                return None, f"Conversion failed: {response.text}"
            
            # Log response for debugging
            response_data = response.json()
            #logger.debug(f"API Response: {json.dumps(response_data, indent=2)}")
            
            # Save JSON response
            json_output_path = company_dir / f"transactions_{datetime.now().strftime('%H%M%S')}.json"
            with open(json_output_path, 'w') as f:
                json.dump(response_data, f, indent=2)
            logger.info(f"Saved JSON output to {json_output_path}")
            
            # Process transactions
            transactions = []
            current_year = datetime.now().year  # Get current year
            
            # Handle nested structure from BSC API
            if response_data and isinstance(response_data, list) and response_data[0].get('normalised'):
                logger.info("Processing normalised transactions from BSC API")
                normalised_transactions = response_data[0]['normalised']
                
                for trans in normalised_transactions:
                    try:
                        amount = Decimal(trans['amount'].replace('$', '').replace(',', ''))
                        date_str = self._standardize_date(trans['date'])
                        
                        transactions.append({
                            'date': date_str,
                            'description': trans['description'],
                            'amount': amount
                        })
                    except (KeyError, InvalidOperation) as e:
                        logger.warning(f"Skipping malformed transaction: {trans}. Error: {str(e)}")
                        continue
                
                logger.info(f"Processed {len(transactions)} transactions from {len(normalised_transactions)} records")
                logger.info(f"Sample transaction date format: {transactions[0]['date'] if transactions else 'No transactions'}")
            else:
                logger.error("Unexpected API response format")
                return None, "Invalid response format from API"
            
            if not transactions:
                logger.warning("No valid transactions found in API response")
                return None, "No valid transactions found"
            
            return transactions, ""
            
        except Exception as e:
            error_msg = f"Error converting PDF: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg 