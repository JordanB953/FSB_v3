import logging
from pathlib import Path
from datetime import datetime

class DebugConfig:
    """Handles debug configuration and logging setup."""
    
    def __init__(self, base_dir: str = "debug_output"):
        self.base_dir = Path(base_dir)
        self.logs_dir = self.base_dir / "logs"
        self.pdfs_dir = self.base_dir / "pdfs"
        self.data_dir = self.base_dir / "extracted_data"
        self.setup_directories()
        self.setup_logging()
    
    def setup_directories(self):
        """Create necessary directories if they don't exist."""
        for dir_path in [self.logs_dir, self.pdfs_dir, self.data_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def setup_logging(self):
        """Configure logging with file and console output."""
        log_file = self.logs_dir / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        # Remove any existing handlers
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
            
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
    def get_debug_path(self, category: str, filename: str) -> Path:
        """Get debug file path for a given category."""
        category_dir = self.base_dir / category
        category_dir.mkdir(parents=True, exist_ok=True)
        return category_dir / filename 