import json
import logging
import requests
import requests.auth
import bs4
import re

'''
Watch queries with:

mysqladmin -h hostname -u username -p -i 1 processlist




'''

class EzidSearch(object):
    BASE_URL = "https://ezid-stg.cdlib.org"

    OBJECT_TYPES = [
        None,
        "Audiovisual",
        "Collection",
        "Dataset",
        "Event",
        "Image",
        "InteractiveResource",
        "Model",
        "PhysicalObject",
        "Service",
        "Software",
        "Sound",
        "Text",
        "Workflow",
        "Other",
    ]

    IDENTIFIER_TYPES = [None, "ark", "doi"]

    ID_STATUS = [None, "public", "reserved", "unavailable"]

    # There are many more...
    ADMIN_ONWER_SELECTED_SUBSET = [
        None,
        "user_admin",
        "group_admin",
        "group_apitest",
        "user_apitest",
        "group_aublib",
    ]

    TARGET_SEARCH = "search"
    TARGET_MANAGE = "manage"

    RESULTS_RE = re.compile("of\s([,0-9]*)\sSearch")

    def __init__(self):
        self._session = requests.Session()

    def getLogger(self):
        return logging.getLogger("EzidSearch")

    def logResponse(self, r):
        L = self.getLogger()
        L.info("Request: %s", r.url)
        L.info("Elapsed: %s", r.elapsed)
        L.info("Status: %s", r.status_code)
        L.info("Message: %s", r.reason)

    def login(self, username, passwd):
        url = f"{EzidSearch.BASE_URL}/login"
        response = self._session.get(url, auth=(username, passwd))
        self.logResponse(response)

    def logout(self):
        url = f"{EzidSearch.BASE_URL}/logout"
        response = self._session.get(url)
        self.logResponse(response)

    def parseSearchResults(self, body):
        # TODO: returns only the first page of hits
        # #page-directselect-bottom
        soup = bs4.BeautifulSoup(body, features="lxml")
        res = {"total": -1, "records": []}
        tbl = soup.find("table", class_="table3")
        if tbl is None:
            return res
        for tr in tbl.find_all("tr"):
            row = []
            for td in tr.find_all("td"):
                row.append(td.text.strip())
            res["records"].append(row)
        result_count = soup.select("body > div.customize-table > form > h2")
        if len(result_count) > 0:
            _txt = result_count[0].text

            matches = EzidSearch.RESULTS_RE.search(_txt)
            if matches is not None:
                _total = matches.group(1).replace(",", "")
                res["total"] = int(_total)
        return res

    def search(self, query, target=None):
        if target is None:
            target = EzidSearch.TARGET_SEARCH
        assert query.get("object_type", None) in EzidSearch.OBJECT_TYPES
        assert query.get("id_type", None) in EzidSearch.IDENTIFIER_TYPES
        url = f"{EzidSearch.BASE_URL}/{target}"
        headers = {"Accept": "application/json"}
        params = {}
        for k, v in query.items():
            if not v is None:
                params[k] = v
        response = self._session.get(url, headers=headers, params=params)
        res = {
            "results": self.parseSearchResults(response.text),
            "url": response.url,
            "status": response.status_code,
            "elapsed": response.elapsed,
        }
        return res

    def blankQueryForm(self, manager=False):
        query_form = {
            "keywords": None,
            "identifier": None,
            "title": None,
            "creator": None,
            "publisher": None,
            "pubyear_from": None,
            "pubyear_to": None,
            "object_type": None,
            "id_type": None,
            "filtered": None,  # "t",  # hidden
        }
        if not manager:
            return query_form

        manage_query_form = {
            "target": None,
            "create_time_from": None,
            "create_time_to": None,
            "update_time_from": None,
            "update_time_to": None,
            "id_status": None,
            "harvesting": None,  # True or False
            "hasMetadata": None,  # True or False
            "owner_selected": None,  # populated from service
        }
        query_form.update(manage_query_form)
        return query_form
