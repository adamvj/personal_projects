import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time

def create_session():
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = create_session()

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/',
    'Upgrade-Insecure-Requests': '1'
}

def test_url(url, name):
    print(f"Testing {name}: {url}")
    start = time.time()
    try:
        response = session.get(url, headers=headers, timeout=10)
        elapsed = time.time() - start
        print(f"Status: {response.status_code} | Time: {elapsed:.2f}s")
        if response.status_code == 200:
            print("Success! Content length:", len(response.content))
        else:
            print("Failed with status code:", response.status_code)
    except Exception as e:
        print(f"Failed with error: {e}")

if __name__ == "__main__":
    print("Starting Diagnostic...")
    # Test 1: Main Cap Page
    test_url("https://www.spotrac.com/nfl/cap/2024/", "Main Cap Page")
    
    # Test 2: Specific Team Page (Bills)
    test_url("https://www.spotrac.com/nfl/buffalo-bills/cap/2024/", "Bills Team Page")
    
    # Test 3: Specific Team Page (49ers - commonly problematic if slug wrong)
    test_url("https://www.spotrac.com/nfl/san-francisco-49ers/cap/2024/", "49ers Team Page")
