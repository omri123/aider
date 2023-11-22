import requests


def getTitles(port):
    # http://localhost:8080/add/titles
    URL = "http://localhost:" + str(port) + "/add" + "/titles"
    r = requests.get(url=URL, timeout=0.2)
    if r.status_code == 404:
        return []
    return r.text.split("\n")


def getContent(port, title):
    # http://localhost:8080/add/content/<title>
    URL = "http://localhost:" + str(port) + "/add" + "/content" + "/" + title
    print(URL)
    r = requests.get(url=URL, timeout=5)
    if r.status_code == 404:
        return None
    return r.text
