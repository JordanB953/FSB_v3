import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Add the root directory to Python path
root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from app.categorization.fuzzy_matcher import FuzzyMatcher
from app.categorization.ai_categorizer import AICategorizer

logging.basicConfig(level=logging.INFO)

def test_categorization():
    # Get absolute paths using Path
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent
    
    # Construct absolute paths for all files
    industry_dict_path = root_dir / "app" / "dictionaries" / "restaurant_categories.csv"
    general_dict_path = root_dir / "app" /  "dictionaries" / "general_categories.csv"
    test_json_path = test_dir / "test_transactions.json"
    
    # Ensure directories exist
    (root_dir / "app" / "categorization" / "dictionaries").mkdir(exist_ok=True)
    
    # Initialize both categorizers
    matcher = FuzzyMatcher(
        industry_dictionary_path=str(industry_dict_path),
        general_dictionary_path=str(general_dict_path)
    )
    
    ai_categorizer = AICategorizer(
        industry_dictionary_path=str(industry_dict_path),
        general_dictionary_path=str(general_dict_path)
    )
    
    # Process transactions through fuzzy matching
    transactions = matcher.process_json_transactions(
        json_path=str(test_json_path),
        confidence_threshold=0.8
    )
    
    # Find transactions needing LLM categorization
    llm_needed = [
        trans for trans in transactions
        if (trans['industry-dictionary-category-confidence-level'] < 0.8 and
            trans['general-dictionary-category-confidence-level'] < 0.8)
    ]
    
    # Process with LLM if needed
    if llm_needed:
        logger.info(f"Processing {len(llm_needed)} transactions with LLM")
        llm_results = ai_categorizer.process_transactions(llm_needed)
        
        # Update original transactions with LLM results
        for trans in transactions:
            matching_result = next(
                (r for r in llm_results if r['short-description'] == trans['short-description']),
                None
            )
            if matching_result:
                trans['llm_category'] = matching_result['llm_category']
                trans['llm_confidence'] = matching_result['llm_confidence']
    
    # Print results in a readable format
    print("\nProcessed Transactions:")
    print("=" * 80)
    for idx, trans in enumerate(transactions, 1):
        print(f"\nTransaction {idx}:")
        print(f"Description: {trans['description']}")
        print(f"Short Description: {trans['short-description']}")
        print(f"Industry Category: {trans['industry-dictionary-category']} "
              f"(Confidence: {trans['industry-dictionary-category-confidence-level']:.2f})")
        print(f"General Category: {trans['general-dictionary-category']} "
              f"(Confidence: {trans['general-dictionary-category-confidence-level']})")
        print(f"LLM Category: {trans.get('llm_category', 'N/A')} "
              f"(Confidence: {trans.get('llm_confidence', 'N/A')})")
        print("-" * 40)

if __name__ == "__main__":
    test_categorization()