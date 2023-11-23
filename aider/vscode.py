"""Client for additional context server

The server is implemented as part of aider-vscode extension.
This client is meant to be used by "add" command and its auto-completion.
"""

import requests


def get_prefixes(port):
    """return a list of reserved title prefixes

    URL format is http://localhost:8080/add/prefixes
    """

    URL = "http://localhost:" + str(port) + "/add" + "/prefixes"
    r = requests.get(url=URL, timeout=0.2)
    if r.status_code != 200:
        raise Exception("Error getting prefixes, status code: " + str(r.status_code))
    return r.text.strip().split("\n")


def get_titles(port):
    """return a list of titles for available context items

    URL format is http://localhost:8080/add/titles
    """

    URL = "http://localhost:" + str(port) + "/add" + "/titles"
    r = requests.get(url=URL, timeout=0.2)
    if r.status_code != 200:
        raise Exception("Error getting titles, status code: " + str(r.status_code))
    return r.text.strip().split("\n")


def get_content(port, title):
    """return the content of the context item with the given title

    URL format is http://localhost:8080/add/content/<title>
    """

    URL = "http://localhost:" + str(port) + "/add" + "/content" + "/" + title
    r = requests.get(url=URL, timeout=5)
    if r.status_code != 200:
        raise Exception("Error getting content, status code: " + str(r.status_code))
    return r.text
