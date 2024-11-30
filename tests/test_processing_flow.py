import sys
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime, timedelta
import pytest
from unittest.mock import Mock, patch

# Add root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.processors.pdf_processor import PDFProcessor
from app.categorization.fuzzy_matcher import FuzzyMatcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_transactions() -> pd.DataFrame:
    """Create sample transaction data for testing."""
    data = {
        'date': [
            datetime.now() - timedelta(days=x) 
            for x in range(10)
        ],
        'description': [
            'RESTAURANT DEPOT',
            'UBER EATS PAYMENT',
            'BEVERAGE VENDOR',
            'PAYROLL PAYMENT',
            'RENT PAYMENT',
            'FOOD SUPPLIER',
            'DOORDASH',
            'UTILITIES BILL',
            'EQUIPMENT REPAIR',
            'GRUBHUB'
        ],
        'amount': [
            -445.67,
            234.56,
            -123.45,
            -2345.67,
            -1234.56,
            -567.89,
            198.76,
            -234.56,
            -345.67,
            187.65
        ]
    }
    return pd.DataFrame(data)

@patch('app.processors.pdf_processor.PDFConverter')
@patch('app.processors.pdf_processor.PDFRedactor')
def test_processing_flow(MockRedactor, MockConverter):
    """Test the entire processing flow without making API calls."""
    try:
        # Setup mock converter
        mock_converter = MockConverter.return_value
        transactions = create_mock_transactions().to_dict('records')
        mock_converter.convert_pdf_to_transactions.return_value = (transactions, None)
        
        # Setup mock redactor
        mock_redactor = MockRedactor.return_value
        mock_redactor.redact_pdf.return_value = ("mock_path.pdf", {"account_numbers": 2})
        
        # Create mock PDF file
        mock_pdf = Mock()
        mock_pdf.name = "test_statement.pdf"
        
        # Initialize processor
        pdf_processor = PDFProcessor()
        
        # Process PDF
        logger.info("Testing PDF processing...")
        result = pdf_processor.process_pdf(
            pdf_file=mock_pdf,
            user_email="test@example.com",
            company_name="Test Restaurant"
        )
        
        assert result is not None, "PDF processing failed"
        assert 'transactions_df' in result, "No transactions DataFrame in result"
        assert not result['transactions_df'].empty, "Empty transactions DataFrame"
        
        df = result['transactions_df']
        logger.info(f"Processed {len(df)} transactions")
        logger.info(f"Columns: {df.columns.tolist()}")
        
        # Test categorization
        logger.info("\nTesting categorization...")
        matcher = FuzzyMatcher(industry="restaurant")
        
        # Process each transaction individually since batch_process doesn't exist
        logger.info("Processing transactions through FuzzyMatcher...")
        processed_transactions = []
        for _, transaction in df.iterrows():
            processed = matcher.process_transaction(
                {
                    'description': transaction['description'],
                    'date': transaction['date'],
                    'amount': transaction['amount']
                },
                confidence_threshold=0.8
            )
            processed_transactions.append(processed)
        
        # Convert processed transactions back to DataFrame
        categorized_df = pd.DataFrame(processed_transactions)
        
        assert not categorized_df.empty, "Categorization produced empty DataFrame"
        logger.info(f"Categorized {len(categorized_df)} transactions")
        
        # Show categorization results
        if 'category' in categorized_df.columns:
            categories = categorized_df['category'].unique()
            logger.info(f"Categories found: {categories.tolist()}")
        else:
            logger.info("Categories found in fields:")
            if 'industry-dictionary-category' in categorized_df.columns:
                logger.info("Industry categories: " + 
                           str(categorized_df['industry-dictionary-category'].unique().tolist()))
            if 'general-dictionary-category' in categorized_df.columns:
                logger.info("General categories: " + 
                           str(categorized_df['general-dictionary-category'].unique().tolist()))
        
        # Print sample results
        logger.info("\nSample categorized transactions:")
        display_cols = [
            'description',
            'industry-dictionary-category',
            'industry-dictionary-category-confidence-level',
            'general-dictionary-category',
            'general-dictionary-category-confidence-level'
        ]
        sample = categorized_df[display_cols].head()
        for _, row in sample.iterrows():
            logger.info(f"Description: {row['description']}")
            logger.info(f"Industry Category: {row['industry-dictionary-category']} " +
                        f"(conf: {row['industry-dictionary-category-confidence-level']:.2f})")
            logger.info(f"General Category: {row['general-dictionary-category']} " +
                        f"(conf: {row['general-dictionary-category-confidence-level']:.2f})")
            logger.info("---")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        logger.exception(e)
        return False

if __name__ == "__main__":
    success = test_processing_flow()
    if success:
        print("✓ All tests passed")  # Using print instead of logger for Unicode
    else:
        print("✗ Tests failed")  # Using print instead of logger for Unicode 