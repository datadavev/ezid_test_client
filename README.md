# README for ezid_pyppeteer

Provides client oriented testing of EZID.

## Installation

Install poetry:

```
pip install poetry 
```

Clone this repo:

```
git clone https://github.com/datadavev/ezid_test_client.git
```

Install dependencies (and optionally create virtualenv if not in one)

```
cd ezid_test_client
poetry install
```


Run tests:

```
ssh -L 18880:localhost:18880 ezid-stage
pytest
```

To adjust browser size:
```
pytest \
  --executable-path '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --window-size 1200 800
```

Run a specific test, e.g., test anonymouse DOI generation:
```
pytest \
  --executable-path '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  --window-size 1200 800 \
  test_basic.py::test_mint_anonymous_doi
```
