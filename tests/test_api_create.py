import os
import requests
import pytest
import codecs
import re
import time
import datetime
import json
from benedict import benedict
import logging

CROSSREF_TEST = """<?xml version="1.0"?>
<book xmlns="http://www.crossref.org/schema/4.3.4"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.crossref.org/schema/4.3.4
  http://www.crossref.org/schema/deposit/crossref4.3.4.xsd"
  book_type="monograph">
  <book_metadata>
    <contributors>
      <person_name contributor_role="author" sequence="first">
        <given_name>Marcel</given_name>
        <surname>Proust</surname>
      </person_name>
    </contributors>
    <titles>
      <title>Remembrance of Things Past</title>
    </titles>
    <doi_data>
      <doi>(:tba)</doi>
      <resource>(:tba)</resource>
    </doi_data>
  </book_metadata>
</book>
"""

def dictsEqual(a, b):
    _a = json.dumps(a, sort_keys=True, indent=2)
    _b = json.dumps(b, sort_keys=True)
    print("A")
    print(_a)
    print("B")
    print(_b)
    return _a == _b


def formatAnvlRequest(args, encoding="utf-8"):
    """
    Generate ANVL erquest document from provided arguments

    Args:
        args: list of [k,v, k,v, k,v, ...]
        encoding: encoding for generated document

    Returns:
        test, ANVL formatted document
    """
    request = []
    for i in range(0, len(args), 2):
        # k = args[i].decode(encoding)
        k = args[i]
        if k == "@":
            f = codecs.open(args[i + 1], encoding=encoding)
            request += [l.strip("\r\n") for l in f.readlines()]
            f.close()
        else:
            if k == "@@":
                k = "@"
            else:
                k = re.sub("[%:\r\n]", lambda c: f"%{ord(c.group(0)):02X}", k)
            # v = args[i + 1].decode(encoding)
            v = args[i + 1]
            if v.startswith("@@"):
                v = v[1:]
            elif v.startswith("@") and len(v) > 1:
                f = codecs.open(v[1:], encoding=encoding)
                v = f.read()
                f.close()
            v = re.sub("[%\r\n]", lambda c: f"%{ord(c.group(0)):02X}", v)
            request.append(f"{k}: {v}")
    return "\n".join(request)


def anvlRequestFromDict(d):
    args = []
    for k, v in d.items():
        args.append(k)
        args.append(v)
    return formatAnvlRequest(args)


def anvlresponseToDict(
    response, format_timestamps=True, decode=False, _encoding="utf-8"
):
    res = {"status": "unknown", "status_message": "no content", "body": ""}
    if response is None:
        return res
    response = response.splitlines()
    # Treat the first response line as the status
    K, V = response[0].split(":", 1)
    res["status"] = K
    res["status_message"] = V.strip(" ")
    for line in response[1:]:
        try:
            K, V = line.split(":", 1)
            V = V.strip()
            if format_timestamps and (K == "_created:" or K == "_updated:"):
                ls = line.split(":")
                V = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(int(ls[1])))
            if decode:
                V = re.sub(
                    "%([0-9a-fA-F][0-9a-fA-F])", lambda m: chr(int(m.group(1), 16)), V,
                )
            res[K] = V
        except ValueError:
            res["body"] += line
    return res


def getRetry(url, headers=None, cookies=None, params=None, maxtime=30, status_codes=[200, 201]):
    t0 = time.time()
    while True:
        res = requests.get(url, cookies=cookies, headers=headers, params=params)
        logging.info("%s: %s", res.status_code, res.url)
        if res.status_code in status_codes:
            return res
        time.sleep(3.0)
        t1 = time.time()
        if (t1-t0) > maxtime:
            break
    return None


@pytest.fixture(scope="module")
def auth_token(ezid_base):
    ezid_user = os.environ.get("EZID_USER", None)
    ezid_pass = os.environ.get("EZID_PASS", None)
    url = f"{ezid_base}/login"
    res = requests.get(url, auth=(ezid_user, ezid_pass))
    assert res.status_code == 200
    assert res.status_code == 200
    token = res.cookies.get("sessionid", None)
    assert token is not None
    return token


def test_serverUp(ezid_base):
    res = requests.get(f"{ezid_base}/")
    assert res.status_code == 200


def test_staticContent(ezid_base):
    url = f"{ezid_base}/static/stylesheets/main.css"
    res = requests.get(url)
    assert res.status_code == 200


def test_apiStatus(ezid_base):
    url = f"{ezid_base}/status"
    res = requests.get(url)
    assert res.status_code == 200
    assert res.text.find("success") >= 0


def test_apiLogin(ezid_base):
    ezid_user = os.environ.get("EZID_USER", None)
    ezid_pass = os.environ.get("EZID_PASS", None)
    url = f"{ezid_base}/login"
    res = requests.get(url, auth=(ezid_user, ezid_pass))
    assert res.status_code == 200
    token = res.cookies.get("sessionid", None)
    assert token is not None


def test_apiMintARK(ezid_base, auth_token):
    tnow = datetime.datetime.now(tz=datetime.timezone.utc)
    shoulder = "ark:/99999/fk4"
    metadata = {
        "target": "http://example.net/",
        "erc.who": "ezid-testing",
        "erc.what": "test case",
        "erc.when": tnow.isoformat(),
    }
    url = f"{ezid_base}/shoulder/{shoulder}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)

    anvl = anvlRequestFromDict(metadata)
    res = requests.post(url, cookies=cookies, data=anvl, headers=headers)
    assert res.status_code in [200, 201]
    match = re.match(r"^success:\s*(.*)$", res.text)
    _id = match.group(1)
    url = f"{ezid_base}/id/{_id}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)
    res = requests.get(url, cookies=cookies, headers=headers)
    assert res.status_code in [
        200,
    ]
    data = anvlresponseToDict(res.text)
    for k,v in metadata.items():
        assert data[k] == v


def test_apiMintDataCiteDOI(ezid_base, auth_token):
    tnow = datetime.datetime.now(tz=datetime.timezone.utc)
    shoulder = "doi:10.21418/G8"
    metadata = {
        "target": "http://example.net/",
        "erc.who": "ezid-testing",
        "erc.what": "test case",
        "erc.when": tnow.isoformat(),
        "datacite.creator": "Dave",
        "datacite.title": "test-title",
        "datacite.publisher": "test-publisher",
        "datacite.publicationyear":str(2021),
        "datacite.resourcetype":"Other",
    }
    url = f"{ezid_base}/shoulder/{shoulder}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)

    anvl = anvlRequestFromDict(metadata)
    res = requests.post(url, cookies=cookies, data=anvl, headers=headers)
    print("\n========")
    print(res.text)
    print("========")
    assert res.status_code in [200, 201]
    match = re.match(r"^success:\s*(\S*)\s.*", res.text)
    _id = match.group(1)
    print(f"_id = {_id}")
    #
    # Verify returned identifier has expected metadata
    url = f"{ezid_base}/id/{_id}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)
    res = requests.get(url, cookies=cookies, headers=headers)
    assert res.status_code in [
        200,
    ]
    data = anvlresponseToDict(res.text)
    for k,v in metadata.items():
        assert data[k] == v
    #
    # Check DataCite to see if the identifier is there
    doi = _id.split(":")[1]
    url = f"https://api.test.datacite.org/dois/{doi}"
    res = getRetry(url, status_codes=[200,201])
    assert res is not None
    data = json.loads(res.text)
    assert data.get("data",{}).get("id","").lower() == doi.lower()
    print(json.dumps(res.text, indent=2))

'''
See https://hackmd.io/@nenuji/BytJrAyQY

'''
def test_apiMintCrossRefDOI(ezid_base, auth_token):
    tnow = datetime.datetime.now(tz=datetime.timezone.utc)
    shoulder = "doi:10.15697/"
    metadata = {
        "target": "http://example.net/",
        "erc.who": "ezid-testing",
        "erc.what": "test case",
        "erc.when": tnow.isoformat(),
        "datacite.creator": "Dave",
        "datacite.title": "test-title",
        "datacite.publisher": "test-publisher",
        "datacite.publicationyear":str(2021),
        "datacite.resourcetype":"Other",
        "crossref": CROSSREF_TEST
    }
    url = f"{ezid_base}/shoulder/{shoulder}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)

    anvl = anvlRequestFromDict(metadata)
    res = requests.post(url, cookies=cookies, data=anvl, headers=headers)
    #print("\n========")
    #print(res.text)
    #print("========")
    assert res.status_code in [200, 201]
    match = re.match(r"^success:\s*(\S*)\s.*", res.text)
    _id = match.group(1)
    logging.info(f"_id = {_id}")
    #
    # Verify returned identifier has expected metadata
    url = f"{ezid_base}/id/{_id}"
    headers = {"Content-Type": "text/plain; charset=UTF-8"}
    cookies = dict(sessionid=auth_token)
    res = requests.get(url, cookies=cookies, headers=headers)
    assert res.status_code in [
        200,
    ]
    #print(res.text)
    data = anvlresponseToDict(res.text, decode=True)

    logging.debug(json.dumps(data, indent=2))

    ignored_paths = [
        "book",
        "book.@xsi:schemaLocation",
        "book.book_metadata",
        "book.book_metadata.doi_data",
        "book.book_metadata.doi_data.doi",
        "book.book_metadata.doi_data.resource",
    ]
    for k,v in metadata.items():
        if k == "crossref":
            a = benedict(data[k], format="xml")
            print(a.to_json(indent=2))
            b = benedict(v, format="xml")
            paths = a.keypaths(indexes=False)
            for _path in paths:
                if _path not in ignored_paths:
                    logging.debug(_path)
                    assert a[_path] == b[_path]
        else:
            assert data[k] == v
    #print("NEXT")
    #
    # Check CrossRef to see if the identifier is there
    #
    # This is actually a PITA. The crossref API does not
    # seem to support access to the test site, so the fallback
    # is to make a request to the test admin site, but that requires
    # a submission id that may be returned to ezid, but is not
    # forwarded to the client. The only way to get it would be
    # something like:
    # 1. authenticate with crossref test
    # 2. get the list of submissions from
    #      https://test.crossref.org/servlet/submissionAdmin?sf=showQ#55150
    # 3. Get the submission id, and make a request to
    #      https://test.crossref.org/servlet/submissionAdmin?sf=content&submissionID=1432407983
    # Requests in 2 & 3 require authentication
    doi = _id.split(":")[1]
    print(f"Crossref test DOI = {doi}")
    #url = f"https://api.crossref.org/works/{doi}"
    #res = getRetry(url, status_codes=[200, 201, ])
    #assert res is not None
    #data = json.loads(res.text)
    #assert data.get("data",{}).get("id","").lower() == doi.lower()
    #print(json.dumps(res.text, indent=2))



def test_apiLogout(ezid_base, auth_token):
   url = f"{ezid_base}/logout"
   cookies = dict(sessionid=auth_token)
   res = requests.get(url, cookies=cookies)
   assert res.status_code == 200
