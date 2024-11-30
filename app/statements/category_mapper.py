from pathlib import Path
import json
import logging
from typing import Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CategoryMapper:
    """Handles loading and managing category structures for financial statements."""
    
    def __init__(self, industry: str):
        """
        Initialize CategoryMapper with specific industry configuration.
        
        Args:
            industry: String identifier for the industry (e.g., 'restaurant')
        """
        self.industry = industry
        self.config = self._load_industry_config()
        
    def _load_industry_config(self) -> Dict:
        """
        Load category configuration from JSON file.
        
        Returns:
            Dictionary containing category configuration
        
        Raises:
            FileNotFoundError: If industry config file doesn't exist
            JSONDecodeError: If config file is invalid JSON
        """
        config_path = Path(__file__).parent.parent / 'config' / 'industry_categories' / f'{self.industry}.json'
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded category configuration for {self.industry}")
            return config
        except FileNotFoundError:
            logger.error(f"Category configuration not found for industry: {self.industry}")
            raise
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in category configuration for industry: {self.industry}")
            raise

    def get_category_structure(self) -> List[Dict]:
        """
        Get ordered list of categories and subcategories for Excel generation.
        
        Returns:
            List of dictionaries containing category information, ordered by display_order
        """
        structure = []
        categories = self.config['categories']
        
        # Sort parent categories by display order
        sorted_parents = sorted(
            categories.items(),
            key=lambda x: x[1]['display_order']
        )
        
        for parent_name, parent_data in sorted_parents:
            # Add parent category info
            structure.append({
                'parent': parent_name,
                'name': parent_name,
                'is_parent': True,
                'is_total': False,
                'prefix': parent_name
            })
            
            # Add subcategories
            for sub_name, sub_data in parent_data['subcategories'].items():
                structure.append({
                    'parent': parent_name,
                    'name': sub_name,
                    'is_parent': False,
                    'is_total': False,
                    'prefix': sub_data['prefix']
                })
            
            # Add total row for parent category
            structure.append({
                'parent': parent_name,
                'name': f'Total {parent_name}',
                'is_parent': False,
                'is_total': True,
                'prefix': f'Total {parent_name}'
            })
            
        return structure

    def get_parent_categories(self) -> List[str]:
        """
        Get list of parent categories in display order.
        
        Returns:
            List of parent category names
        """
        return [
            name for name, data in sorted(
                self.config['categories'].items(),
                key=lambda x: x[1]['display_order']
            )
        ]

    def get_subcategories(self, parent: str) -> List[str]:
        """
        Get subcategories for a parent category.
        
        Args:
            parent: Name of parent category
            
        Returns:
            List of subcategory names
            
        Raises:
            KeyError: If parent category doesn't exist
        """
        try:
            return list(self.config['categories'][parent]['subcategories'].keys())
        except KeyError:
            logger.error(f"Parent category not found: {parent}")
            raise

    def get_category_prefix(self, parent: str, subcategory: str) -> Optional[str]:
        """
        Get full category prefix for a subcategory.
        
        Args:
            parent: Parent category name
            subcategory: Subcategory name
            
        Returns:
            Category prefix or None if not found
        """
        try:
            return self.config['categories'][parent]['subcategories'][subcategory]['prefix']
        except KeyError:
            logger.error(f"Category prefix not found for {parent} -> {subcategory}")
            return None

    def validate_category(self, category: str) -> bool:
        """
        Check if a category prefix is valid.
        
        Args:
            category: Category prefix to validate
            
        Returns:
            True if category is valid, False otherwise
        """
        for parent_data in self.config['categories'].values():
            for sub_data in parent_data['subcategories'].values():
                if sub_data['prefix'] == category:
                    return True
        return False