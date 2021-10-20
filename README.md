# README for ezid_pyppeteer

Uses virtualenv called "mariabot"

Run pytest with
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


