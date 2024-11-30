print("Loading AI Categorizer")
from anthropic import Anthropic
from typing import List, Dict, Optional, Set
import logging
import os
from dotenv import load_dotenv
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("Defining AICategorizer")
class AICategorizer:
    """Handles transaction categorization using AI API."""
    
    def __init__(self, industry_dictionary_path: str, general_dictionary_path: str):
        """
        Initialize AI API client and load valid categories.
        
        Args:
            industry_dictionary_path: Path to industry-specific category dictionary
            general_dictionary_path: Path to general category dictionary
        """
        # Initialize API
        self.api_key = os.getenv('AI_API_KEY')
        if not self.api_key:
            raise ValueError("AI_API_KEY not found in environment variables")
        
        self.client = Anthropic(api_key=self.api_key)
        
        # Load categories from dictionaries
        self.valid_categories = self._load_valid_categories(
            industry_dictionary_path,
            general_dictionary_path
        )
        
        # Configuration
        self.batch_size = 5  # Number of transaction groups per batch
        
    def _load_valid_categories(self, industry_path: str, general_path: str) -> Set[str]:
        """
        Load and combine unique categories from both dictionaries.
        
        Args:
            industry_path: Path to industry-specific dictionary
            general_path: Path to general dictionary
            
        Returns:
            Set of unique valid categories
        """
        categories = set()
        
        try:
            # Load industry dictionary
            industry_df = pd.read_csv(industry_path)
            if 'category' in industry_df.columns:
                categories.update(industry_df['category'].unique())
            
            # Load general dictionary
            general_df = pd.read_csv(general_path)
            if 'category' in general_df.columns:
                categories.update(general_df['category'].unique())
            
            logger.info(f"Loaded {len(categories)} unique categories from dictionaries")
            return categories
            
        except Exception as e:
            logger.error(f"Error loading categories from dictionaries: {str(e)}")
            raise

    def _create_prompt(self, transaction_groups: List[Dict]) -> str:
        """
        Create a prompt for Claude to categorize transaction groups.
        
        Args:
            transaction_groups: List of transaction group dictionaries
            
        Returns:
            Formatted prompt string
        """
        try:
            categories_str = ", ".join(sorted(self.valid_categories))
            
            prompt = f"""
            Your task is to categorize transaction groups. You must choose from these categories only:
            {categories_str}

            Guidelines:
            1. Analyze the transaction pattern (frequency and amounts) for each group
            2. Choose the most appropriate category based on description and patterns
            3. Provide a confidence level between 0 and 1
            4. Only update the llm_category and llm_confidence fields

            Transaction Groups:
            {json.dumps(transaction_groups, indent=2)}

            Respond only with the updated JSON array, filling in llm_category and llm_confidence for each group.
            Ensure your response is valid JSON format.
            """
            
            return prompt
            
        except Exception as e:
            logger.error(f"Error creating prompt: {str(e)}")
            raise

    def _get_categories(self, transaction_groups: List[Dict]) -> List[Dict]:
        """
        Get categorizations from Claude API for a batch of transaction groups.
        
        Args:
            transaction_groups: List of transaction group dictionaries
            
        Returns:
            List of categorized transaction groups
        """
        try:
            prompt = self._create_prompt(transaction_groups)
            
            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1024,
                temperature=0,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            # Parse JSON response
            response_text = message.content[0].text
            categorized_groups = json.loads(response_text)
            
            # Validate results
            validated_groups = []
            for group in categorized_groups:
                if self._validate_group_result(group):
                    validated_groups.append(group)
                else:
                    logger.warning(f"Invalid group result: {group}")
            
            return validated_groups

        except Exception as e:
            logger.error(f"Error calling Claude API: {str(e)}")
            return []

    def _validate_group_result(self, group: Dict) -> bool:
        """
        Validate a single group categorization result.
        
        Args:
            group: Dictionary containing group categorization result
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            if not all(key in group for key in ['short_description', 'llm_category', 'llm_confidence']):
                return False
            
            # Validate category
            if group['llm_category'] not in self.valid_categories:
                return False
            
            # Validate confidence
            if not isinstance(group['llm_confidence'], (int, float)):
                return False
            
            if not (0 <= group['llm_confidence'] <= 1):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating group result: {str(e)}")
            return False

    def batch_categorize(self, df: pd.DataFrame, 
                        batch_size: int = 10) -> pd.DataFrame:
        """
        Categorize transactions in batches.
        
        Args:
            df: DataFrame containing transactions
            batch_size: Number of transactions to process in each API call
            
        Returns:
            DataFrame with added AI categorization columns
        """
        results_df = df.copy()
        results_df['ai_category'] = None
        results_df['ai_confidence'] = 0.0
        results_df['ai_explanation'] = None

        # Process transactions in batches
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i+batch_size]
            
            # Prepare transactions for the batch
            transactions = []
            for idx, row in batch.iterrows():
                transactions.append({
                    'id': idx,
                    'description': row['description'],
                    'amount': row['amount']
                })

            # Get categorizations from Claude
            try:
                categories = self._get_categories(transactions)
                
                # Update DataFrame with results
                for result in categories:
                    idx = result['transaction_id']
                    results_df.at[idx, 'ai_category'] = result['category']
                    results_df.at[idx, 'ai_confidence'] = result['confidence']
                    results_df.at[idx, 'ai_explanation'] = result['explanation']
                    
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                continue

        return results_df

    def _group_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Group similar transactions by short description.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of transaction group dictionaries
        """
        try:
            # Create dictionary to hold groups
            groups = {}
            
            for trans in transactions:
                short_desc = trans['short-description']
                
                if short_desc not in groups:
                    groups[short_desc] = {
                        'short_description': short_desc,
                        'amounts': [],
                        'dates': [],
                        'transaction_ids': [],
                        'llm_category': None,
                        'llm_confidence': None
                    }
                
                # Log the date type and value for debugging
                logger.debug(f"Processing date: {type(trans['date'])} - {trans['date']}")
                
                groups[short_desc]['amounts'].append(float(trans['amount']))
                groups[short_desc]['dates'].append(trans['date'])
                groups[short_desc]['transaction_ids'].append(trans.get('id', None))
            
            # Convert groups to list and add frequency information
            grouped_transactions = []
            for group in groups.values():
                # Sort dates for frequency calculation
                group['dates'].sort()
                
                # Calculate frequency
                if len(group['dates']) > 1:
                    date_range = (
                        datetime.strptime(group['dates'][-1], '%Y-%m-%d') - 
                        datetime.strptime(group['dates'][0], '%Y-%m-%d')
                    ).days
                    group['frequency'] = f"{len(group['dates'])} times in {date_range + 1} days"
                else:
                    group['frequency'] = "1 time"
                
                grouped_transactions.append(group)
            
            logger.info(f"Grouped {len(transactions)} transactions into {len(grouped_transactions)} groups")
            return grouped_transactions
            
        except Exception as e:
            logger.error(f"Error grouping transactions: {str(e)}")
            raise

    def _prepare_batches(self, grouped_transactions: List[Dict]) -> List[List[Dict]]:
        """
        Prepare batches of transaction groups for processing.
        
        Args:
            grouped_transactions: List of transaction group dictionaries
            
        Returns:
            List of batches, where each batch is a list of transaction groups
        """
        try:
            batches = []
            current_batch = []
            
            for group in grouped_transactions:
                current_batch.append(group)
                
                if len(current_batch) >= self.batch_size:
                    batches.append(current_batch)
                    current_batch = []
            
            # Add any remaining transactions
            if current_batch:
                batches.append(current_batch)
            
            logger.info(f"Prepared {len(batches)} batches of transaction groups")
            return batches
            
        except Exception as e:
            logger.error(f"Error preparing batches: {str(e)}")
            raise

    def process_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Process uncategorized transactions through LLM categorization.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of transactions with LLM categorizations added
        """
        try:
            # Group similar transactions
            grouped_transactions = self._group_transactions(transactions)
            
            # Prepare batches
            batches = self._prepare_batches(grouped_transactions)
            
            # Process each batch
            categorized_groups = {}
            for batch in batches:
                try:
                    results = self._get_categories(batch)
                    
                    # Store results by short description for easy lookup
                    for result in results:
                        categorized_groups[result['short_description']] = {
                            'llm_category': result['llm_category'],
                            'llm_confidence': result['llm_confidence']
                        }
                        
                except Exception as e:
                    logger.error(f"Error processing batch: {str(e)}")
                    continue
            
            # Update original transactions with LLM results
            processed_transactions = []
            for trans in transactions:
                processed_trans = trans.copy()
                
                # Look up categorization by short description
                group_result = categorized_groups.get(trans['short-description'])
                if group_result:
                    processed_trans['llm_category'] = group_result['llm_category']
                    processed_trans['llm_confidence'] = group_result['llm_confidence']
                else:
                    # If no result found, mark as uncategorized
                    processed_trans['llm_category'] = None
                    processed_trans['llm_confidence'] = None
                
                processed_transactions.append(processed_trans)
            
            # Log processing statistics
            total = len(processed_transactions)
            categorized = sum(1 for t in processed_transactions if t['llm_category'] is not None)
            
            logger.info(f"Processing complete:")
            logger.info(f"- Total transactions: {total}")
            logger.info(f"- Successfully categorized: {categorized}")
            logger.info(f"- Uncategorized: {total - categorized}")
            
            return processed_transactions
            
        except Exception as e:
            logger.error(f"Error processing transactions: {str(e)}")
            raise