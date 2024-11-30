import sys
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime, timedelta

# Add root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app.statements import generate_financial_statements, CategoryMapper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sample_transactions() -> pd.DataFrame:
    """Create a sample transactions DataFrame for testing."""
    
    # Create date range for last 3 months
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create sample transactions
    transactions = []
    
    # Revenue transactions
    for date in dates[::3]:  # Every 3rd day
        transactions.append({
            'Date': date,
            'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
            'Description': 'Toast Deposit',
            'Category': 'Revenue: Dine-in',
            'Amount': 345.67
        })
        
        if date.day > 15:  # Catering twice a month
            transactions.append({
                'Date': date,
                'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
                'Description': 'Catering Payment',
                'Category': 'Revenue: Catering',
                'Amount': 789.12
            })
    
    # Cost transactions
    for date in dates[::7]:  # Weekly expenses
        transactions.append({
            'Date': date,
            'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
            'Description': 'Restaurant Depot',
            'Category': 'Cost of Sales: Food',
            'Amount': -445.67
        })
        
        transactions.append({
            'Date': date,
            'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
            'Description': 'Beverage Vendor',
            'Category': 'Cost of Sales: Beverages',
            'Amount': -123.45
        })
    
    # Operating expenses (monthly)
    for date in dates[dates.day == 1]:  # First of each month
        transactions.append({
            'Date': date,
            'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
            'Description': 'Payroll',
            'Category': 'Operating Expenses: Payroll',
            'Amount': -2345.67
        })
        
        transactions.append({
            'Date': date,
            'End_of_Month': date.replace(day=1) + pd.offsets.MonthEnd(0),
            'Description': 'Rent Payment',
            'Category': 'Operating Expenses: Rent',
            'Amount': -1234.56
        })
    
    return pd.DataFrame(transactions)

def test_category_mapper():
    """Test CategoryMapper functionality."""
    try:
        # Initialize CategoryMapper
        mapper = CategoryMapper("restaurant")
        
        # Test category structure
        structure = mapper.get_category_structure()
        logger.info("Category structure loaded successfully")
        logger.info(f"Found {len(structure)} categories")
        
        # Test parent categories
        parents = mapper.get_parent_categories()
        logger.info(f"Parent categories: {parents}")
        
        # Test subcategories
        for parent in parents:
            subs = mapper.get_subcategories(parent)
            logger.info(f"Subcategories for {parent}: {subs}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error testing CategoryMapper: {str(e)}")
        return False

def test_statement_generation():
    """Test financial statement generation."""
    try:
        # Create sample transactions
        df = create_sample_transactions()
        logger.info(f"Created {len(df)} sample transactions")
        
        # Generate statements
        output_path = generate_financial_statements(
            transactions_df=df,
            company_name="Test Restaurant",
            industry="restaurant"
        )
        
        if output_path:
            logger.info(f"Successfully generated statements: {output_path}")
            return True
        else:
            logger.error("Failed to generate statements")
            return False
            
    except Exception as e:
        logger.error(f"Error testing statement generation: {str(e)}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting tests...")
    
    # Test CategoryMapper
    logger.info("\nTesting CategoryMapper...")
    if test_category_mapper():
        logger.info("✓ CategoryMapper tests passed")
    else:
        logger.error("✗ CategoryMapper tests failed")
    
    # Test Statement Generation
    logger.info("\nTesting Statement Generation...")
    if test_statement_generation():
        logger.info("✓ Statement generation tests passed")
    else:
        logger.error("✗ Statement generation tests failed")

if __name__ == "__main__":
    main()