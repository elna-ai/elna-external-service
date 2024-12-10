from serpapi import GoogleSearch
import os


def search_web(query):
    """Search the web using SERPAPI"""
    key = os.environ["SERP_API_KEY"]
    if not key:
        raise ValueError("SERP API key is missing from userdata")
    params = {
        "q": query,
        "hl": "en",
        "gl": "us",
        "api_key": key
    }
    search = GoogleSearch(params)
    results = search.get_dict()
    if 'answer_box' in results.keys():
        print("Getting result from answer box")
        return results['answer_box']
    else:
        return results['organic_results'][0]
