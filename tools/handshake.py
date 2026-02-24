import requests
from bs4 import BeautifulSoup

def test_bensbites():
    url = "https://www.bensbites.com/"
    print(f"Testing {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Successfully reached Ben's Bites.")
            return True
    except Exception as e:
        print(f"Error reaching Ben's Bites: {e}")
    return False

def test_therundown():
    url = "https://www.therundown.ai/"
    print(f"Testing {url}...")
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Successfully reached The Rundown AI.")
            return True
    except Exception as e:
        print(f"Error reaching The Rundown AI: {e}")
    return False

if __name__ == "__main__":
    b_ok = test_bensbites()
    r_ok = test_therundown()
    if b_ok and r_ok:
        print("\nLINK HANDSHAKE SUCCESSFUL")
    else:
        print("\nLINK HANDSHAKE FAILED")
