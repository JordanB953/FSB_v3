import pandas as pd
from pathlib import Path
import logging
from typing import Optional
from .excel_generator import ExcelGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_financial_statements(
    transactions_df: pd.DataFrame,
    company_name: str,
    industry: str = "restaurant"
) -> Optional[str]:
    """
    Generate financial statements Excel file from categorized transactions.
    
    Args:
        transactions_df: DataFrame containing categorized transactions
        company_name: Name of company for filename
        industry: Industry type for category mapping (default: restaurant)
        
    Returns:
        Path to generated Excel file or None if error occurs
    """
    try:
        # Validate input DataFrame
        required_columns = ['Date', 'End_of_Month', 'Description', 'Category', 'Amount']
        missing_columns = [col for col in required_columns if col not in transactions_df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
        # Convert dates if they're not already datetime
        transactions_df['Date'] = pd.to_datetime(transactions_df['Date'])
        transactions_df['End_of_Month'] = pd.to_datetime(transactions_df['End_of_Month'])
        
        # Generate statements
        generator = ExcelGenerator(transactions_df, industry)
        output_path = generator.generate(company_name)
        
        logger.info(f"Successfully generated financial statements for {company_name}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error generating financial statements: {str(e)}")
        return None

def get_output_directory() -> Path:
    """
    Get path to statements output directory.
    
    Returns:
        Path object for statements_output directory
    """
    return Path(__file__).parent.parent.parent / 'statements_output'

def cleanup_old_files(max_files: int = 100):
    """
    Remove oldest files if directory contains more than max_files.
    
    Args:
        max_files: Maximum number of files to keep
    """
    try:
        output_dir = get_output_directory()
        if not output_dir.exists():
            return
            
        # Get list of Excel files sorted by creation time
        files = sorted(
            output_dir.glob('*.xlsx'),
            key=lambda x: x.stat().st_ctime
        )
        
        # Remove oldest files if we have too many
        if len(files) > max_files:
            for file in files[:-max_files]:
                file.unlink()
                logger.info(f"Removed old statement file: {file.name}")
                
    except Exception as e:
        logger.error(f"Error cleaning up old files: {str(e)}")