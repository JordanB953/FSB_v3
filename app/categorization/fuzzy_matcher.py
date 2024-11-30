from thefuzz import fuzz
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union
import logging
from pathlib import Path
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FuzzyMatcher:
    """Handles fuzzy matching of transactions against category dictionaries."""
    
    def __init__(self, industry: str):
        """
        Initialize FuzzyMatcher for a specific industry.
        
        Args:
            industry: Industry name (e.g., 'restaurant', 'retail', etc.)
        """
        self.industry = industry.lower()
        self.dictionaries = self._load_dictionaries()
        self.match_cache = {}

    def _load_dictionaries(self) -> dict:
        """Load industry-specific and general dictionaries."""
        try:
            # Get the app directory path
            app_dir = Path(__file__).resolve().parent.parent
            dict_dir = app_dir / "dictionaries"
            
            # Load general dictionary (always used)
            general_dict = pd.read_csv(dict_dir / "general_categories.csv")
            
            # Load industry-specific dictionary if it exists
            industry_path = dict_dir / f"{self.industry}_categories.csv"
            if industry_path.exists():
                industry_dict = pd.read_csv(industry_path)
            else:
                logger.warning(f"No dictionary found for industry: {self.industry}")
                industry_dict = pd.DataFrame(columns=['short_description', 'category'])
            
            return {
                'general': self._validate_dictionary(general_dict),
                'industry': self._validate_dictionary(industry_dict)
            }
            
        except Exception as e:
            logger.error(f"Error loading dictionaries: {str(e)}")
            raise

    def _validate_dictionary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and clean dictionary DataFrame."""
        required_cols = ['short_description', 'category']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Dictionary must contain columns: {required_cols}")
            
        # Clean up dictionary entries
        df['short_description'] = df['short_description'].str.lower().str.strip()
        return df

    def _create_short_description(self, description: str) -> str:
        """
        Process transaction description into a standardized short description.
        
        Args:
            description: Original transaction description
            
        Returns:
            Processed short description
        """
        try:
            # Convert to string and lowercase
            desc = str(description).lower().strip()
            
            # Cut off after domain extensions (.com, .net, etc.)
            domain_pattern = r'\.(?:com|net|org|edu|gov|io|co|us|uk|ca)[^\s]*'
            desc = re.split(domain_pattern, desc)[0]
            
            # Remove date patterns (including leading numbers)
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}',  # DD/MM or MM/DD
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # DD/MM/YYYY or similar
                r'\b\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?',  # HH:MM or HH:MM:SS with optional AM/PM
            ]
            for pattern in date_patterns:
                desc = re.split(pattern, desc)[0].strip()
            
            # Remove leading numbers and spaces
            desc = re.sub(r'^\d+\s+', '', desc)
            
            # Cut off at sequences of 4 or more consecutive numbers if they're not at the start
            parts = desc.split()
            processed_parts = []
            for part in parts:
                if re.search(r'\d{4,}', part):
                    break
                processed_parts.append(part)
            desc = ' '.join(processed_parts)
            
            # Cut off before special characters (except &) keeping alphanumeric and spaces
            desc = re.split(r'[^a-z0-9\s&]', desc)[0]
            
            # Remove any remaining standalone numbers at the end
            desc = re.sub(r'\s+\d+\s*$', '', desc)
            
            # Clean up extra spaces
            desc = ' '.join(desc.split())
            
            # Truncate to 20 characters
            desc = desc[:20].strip()
            
            logger.debug(f"Short description created: {description} -> {desc}")
            return desc
            
        except Exception as e:
            logger.error(f"Error creating short description: {str(e)}")
            return description[:20]  # Fallback to simple truncation

    def load_transactions_from_json(self, json_path: str) -> List[Dict]:
        """
        Load and validate transaction data from JSON file.
        
        Args:
            json_path: Path to JSON file containing transactions
            
        Returns:
            List of transaction dictionaries
        """
        try:
            # Load JSON file
            with open(json_path, 'r') as f:
                transactions = json.load(f)
            
            # Ensure transactions is a list
            if not isinstance(transactions, list):
                raise ValueError("JSON file must contain a list of transactions")
            
            # Validate required fields for each transaction
            required_fields = {'date', 'description', 'amount'}
            for idx, trans in enumerate(transactions):
                missing_fields = required_fields - set(trans.keys())
                if missing_fields:
                    raise ValueError(
                        f"Transaction at index {idx} missing required fields: {missing_fields}"
                    )
            
            logger.info(f"Successfully loaded {len(transactions)} transactions from {json_path}")
            return transactions
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON file {json_path}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading transactions from {json_path}: {str(e)}")
            raise

    def _find_best_match(self, description: str, dictionary_df: pd.DataFrame) -> Tuple[Optional[str], float]:
        """
        Find the best matching category for a description using fuzzy matching.
        
        Args:
            description: Transaction description to match
            dictionary_df: DataFrame containing the category dictionary
            
        Returns:
            Tuple of (matched category or None, confidence score)
        """
        try:
            # Check cache first
            cache_key = f"{description}:{id(dictionary_df)}"
            if cache_key in self.match_cache:
                return (
                    self.match_cache[cache_key]['category'],
                    self.match_cache[cache_key]['confidence']
                )
            
            best_match = None
            best_score = 0.0
            
            # Compare against each dictionary entry
            for _, row in dictionary_df.iterrows():
                score = fuzz.token_sort_ratio(
                    description,
                    row['short_description']
                ) / 100.0  # Convert to 0-1 scale
                
                if score > best_score:
                    best_score = score
                    best_match = row['category']
            
            # Cache the result
            self.match_cache[cache_key] = {
                'category': best_match,
                'confidence': best_score
            }
            
            return best_match, best_score
            
        except Exception as e:
            logger.error(f"Error finding match for '{description}': {str(e)}")
            return None, 0.0

    def process_transaction(self, transaction: Dict, confidence_threshold: float) -> Dict:
        """
        Process a single transaction through both dictionaries.
        
        Args:
            transaction: Transaction dictionary
            confidence_threshold: Minimum confidence score required for a match
            
        Returns:
            Enriched transaction dictionary with categorization fields
        """
        try:
            # Create short description
            short_desc = self._create_short_description(transaction['description'])
            
            # Start with industry dictionary
            industry_category, industry_confidence = self._find_best_match(
                short_desc,
                self.dictionaries['industry']
            )
            
            # Initialize result with original transaction and new fields
            result = {
                **transaction,
                'short-description': short_desc,
                'industry-dictionary-category': industry_category if industry_category else "N/A",
                'industry-dictionary-category-confidence-level': industry_confidence,
                'general-dictionary-category': "N/A",
                'general-dictionary-category-confidence-level': None,
                'llm-category': "N/A"
            }
            
            # If industry match is below threshold, try general dictionary
            if industry_confidence < confidence_threshold:
                general_category, general_confidence = self._find_best_match(
                    short_desc,
                    self.dictionaries['general']
                )
                
                result.update({
                    'general-dictionary-category': general_category if general_category else "N/A",
                    'general-dictionary-category-confidence-level': general_confidence,
                })
                
                # If general match is also below threshold, mark for LLM processing
                if general_confidence < confidence_threshold:
                    result['llm-category'] = None  # Will be processed by AICategorizer
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return transaction  # Return original transaction if processing fails

    def process_json_transactions(self, json_path: str, confidence_threshold: float = 0.8) -> List[Dict]:
        """
        Process all transactions from a JSON file through the categorization pipeline.
        
        Args:
            json_path: Path to JSON file containing transactions
            confidence_threshold: Minimum confidence score required for a match
            
        Returns:
            List of enriched transaction dictionaries
        """
        try:
            # Load transactions
            transactions = self.load_transactions_from_json(json_path)
            
            # Process each transaction
            processed_transactions = []
            for trans in transactions:
                try:
                    processed_trans = self.process_transaction(
                        trans,
                        confidence_threshold
                    )
                    processed_transactions.append(processed_trans)
                except Exception as e:
                    logger.error(f"Error processing transaction {trans}: {str(e)}")
                    # Add original transaction with error indication
                    trans['processing_error'] = str(e)
                    processed_transactions.append(trans)
            
            logger.info(f"Successfully processed {len(processed_transactions)} transactions")
            
            # Calculate and log matching statistics
            industry_matches = sum(1 for t in processed_transactions 
                                 if t.get('industry-dictionary-category') != "N/A")
            general_matches = sum(1 for t in processed_transactions 
                                if t.get('general-dictionary-category') != "N/A")
            llm_needed = sum(1 for t in processed_transactions 
                           if t.get('llm-category') is None)
            
            logger.info(f"Matching statistics:")
            logger.info(f"- Industry dictionary matches: {industry_matches}")
            logger.info(f"- General dictionary matches: {general_matches}")
            logger.info(f"- Transactions requiring LLM: {llm_needed}")
            
            return processed_transactions
            
        except Exception as e:
            logger.error(f"Error processing transactions from {json_path}: {str(e)}")
            raise