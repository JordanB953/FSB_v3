import requests
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def test_bsc_api():
    # Configuration
    api_key = os.getenv('BSC_API_KEY')
    api_url = 'https://api2.bankstatementconverter.com/api/v1/convert'
    pdf_path = Path('debug_output/pdfs/default_user_at_example.com/bsc-test1_redacted.pdf')
    
    # Print debug info
    print(f"Testing with:")
    print(f"API URL: {api_url}")
    print(f"PDF Path exists: {pdf_path.exists()}")
    print(f"PDF Path absolute: {pdf_path.absolute()}")
    
    # Prepare request
    headers = {'Authorization': f'Bearer {api_key}'}
    files = {'file': open(pdf_path, 'rb')}
    
    # Make request
    print("\nMaking request...")
    response = requests.post(api_url, headers=headers, files=files)
    
    # Print results
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Text: {response.text}")

if __name__ == "__main__":
    test_bsc_api() 