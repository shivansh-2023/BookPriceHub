import requests
import json

def test_search_api():
    url = "http://127.0.0.1:5000/api/search"
    data = {"title": "The Great Gatsby"}
    
    print(f"Sending request to {url} with data: {data}")
    
    try:
        response = requests.post(url, json=data)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print(f"Success! Found {len(results.get('results', []))} results")
            return results
        else:
            print(f"Error response: {response.text}")
            return None
    except Exception as e:
        print(f"Exception occurred: {str(e)}")
        return None

if __name__ == "__main__":
    results = test_search_api()
    if results:
        print(json.dumps(results, indent=2)[:1000] + "...") # Print first 1000 chars
