import dataclasses
from pytest_pyppeteer.models import Browser
import time
import os

#EZID_URL = "https://ezid-stg.cdlib.org"
EZID_URL = "http://localhost:18880"
DEFAULT_TIMEOUT = 5000


@dataclasses.dataclass(init=False)
class Elements:
    logo = "body > header > div > a > picture > img"
    anon_ark_check = "#ark\:\/99999\/fk4"
    loc_input = "#target"
    who_input = "#erc\.who"
    what_input = "#erc\.what"
    when_input = "#erc\.when"
    ark_submit = "#create_form > div.fieldset-stacked.fieldset__top-border.home__fieldset > div.row > div.col-md-2.home__create-button > button"
    id_as_url = "#url_to_copy"
    id_loc_error = "#create_form > div.fieldset-stacked.fieldset__top-border.home__fieldset > div.row > div:nth-child(1) > div > span"

class DoiElements:
    anon_doi_check = "#doi\:10\.5072\/FK2"
    location = "#target"
    creator = "#datacite\.creator"
    title = "#datacite\.title"
    publisher = "#datacite\.publisher"
    pubyear = "#datacite\.publicationyear"
    ob_types = "#datacite\.resourcetype > option"
    ob_select = "#datacite\.resourcetype"
    "#datacite\.resourcetype"
    submit = "#create_form > div.fieldset-stacked.fieldset__top-border.home__fieldset > div.row > div.col-md-2.home__create-button > button"
    loc_error = "#create_form > div.fieldset-stacked.fieldset__top-border.home__fieldset > div.row > div:nth-child(1) > div > span"
    id_as_url = "#url_to_copy"

async def doinput(page, selector, input_str):
    ele = await page.query_locator(selector)
    await page.evaluate(f"(ele) => ele.value='{input_str}'", ele)

async def elementText(page, selector):
    ele = await page.querySelector(selector)
    return await page.evaluate(f"(element) => element.textContent", ele)

async def doLogin(page, ezid_user, ezid_pass):
    await page.goto(EZID_URL)
    _dlg = await page.querySelector("#js-login-modal")
    assert _dlg is not None
    await page.evaluate('(_dlg) => _dlg.style.display = "block"', _dlg)
    await doinput(page, "#username", ezid_user)
    await doinput(page, "#password", ezid_pass)
    await page.click("#login")


async def getMintedDOI(page):
    # body > div.container.vertical-buffer-20 > div:nth-child(3) > div.col-md-8 > div > div.col-md-8.vertical-buffer-bot-md > strong
    # #url_to_copy
    pass

async def test_alive(pyppeteer: Browser):
    page = await pyppeteer.new_page()
    await page.goto(EZID_URL)
    res = await page.query_locator(Elements.logo)
    assert res is not None


async def test_mint_anonymous_ark(pyppeteer: Browser):
    page = await pyppeteer.new_page()
    await page.goto(EZID_URL)
    await page.waitfor(Elements.anon_ark_check)
    await page.click(Elements.anon_ark_check)
    # this should fail with a bad url message
    await page.type(Elements.loc_input, "https://ex")
    await page.type(Elements.who_input, "MariaBot")
    await page.type(Elements.what_input, "test")
    await page.type(Elements.when_input, "now")
    await page.click(Elements.ark_submit)
    await page.waitfor(Elements.id_loc_error, timeout=DEFAULT_TIMEOUT)

    # Fix the url and resubmit
    await page.type(Elements.loc_input, "https://example.net/")
    await page.click(Elements.ark_submit)
    await page.waitfor(Elements.id_as_url, timeout=DEFAULT_TIMEOUT)


async def test_mint_anonymous_doi(pyppeteer: Browser):
    page = await pyppeteer.new_page()
    await page.goto(EZID_URL)
    ele = await page.query_locator(DoiElements.anon_doi_check)
    await page.evaluate("(element) => element.click()", ele)
    await page.waitfor(DoiElements.location, timeout=DEFAULT_TIMEOUT)

    # this should fail with a bad url message
    await page.type(DoiElements.location, "https://example", delay=100 )
    await page.type(DoiElements.creator, "MariaBot")
    await page.type(DoiElements.title, "test")
    await page.type(DoiElements.publisher, "EZID Test Service")
    await page.type(DoiElements.pubyear, "2021")
    await page.select(DoiElements.ob_select, "Other")

    #selector = await page.querySelector(DoiElements.ob_type)
    # #datacite\.resourcetype > option:nth-child(2)
    #option_texts = []
    #for option_ele in await page.querySelectorAll(DoiElements.ob_types):
    #    txt = await page.evaluate("(element) => element.textContent", option_ele)
    #    option_texts.append(txt)
    #print(f"OPTIONS = {', '.join(option_texts)}")

    await page.click(DoiElements.submit)

    await page.waitfor(DoiElements.loc_error, timeout=DEFAULT_TIMEOUT)
    err_val = page.query_locator(DoiElements.loc_error)
    print("###: ",err_val)
    time.sleep(1)
    await doinput(page, DoiElements.location, "")
    await page.type(DoiElements.location, "https://example.net/", delay=200 )
    await page.click(DoiElements.submit)
    await page.waitfor(DoiElements.id_as_url, timeout=DEFAULT_TIMEOUT)
    time.sleep(10)

'''
TODO: currently uses environment variables for auth
'''
async def test_login(pyppeteer: Browser):
    ezid_user = os.environ.get("EZID_USER", None)
    ezid_pass = os.environ.get("EZID_PASS", None)
    assert ezid_user is not None
    assert ezid_pass is not None

    page = await pyppeteer.new_page()
    await page.goto(EZID_URL)
    await doLogin(page, ezid_user, ezid_pass)
    assert ezid_user in await elementText(page, "body > div.header__admin-text")
    time.sleep(3)
