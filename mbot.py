import asyncio
import click
import cmd
import os
import time
import datetime
import json
import pyppeteer.errors
from pyppeteer import launch
import logging
import csv

EZID_URL = "https://ezid-stg.cdlib.org"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 768
ADV_SEARCH_BLANK = {
    "terms": None,
    "identifier": None,
    "title": None,
    "who": None,
    "publisher": None,
    "from": None,
    "to": None,
    "objtype": None,
    "idtype": None,
}

L = logging.getLogger()

JSON_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
"""datetime format string for generating JSON content
"""

DEFAULT_TIMEOUT = 30000


def dtnow():
    """
    Now, with UTC timezone.

    Returns: datetime
    """
    return datetime.datetime.now(datetime.timezone.utc)


def datetimeToJsonStr(dt):
    """
    Render datetime to JSON datetime string

    Args:
        dt: datetime

    Returns: string
    """
    if dt is None:
        return None
    return dt.strftime(JSON_TIME_FORMAT)


async def doClick(page, ele):
    return await page.evaluate("(ele) => ele.click()", ele)


class EZBrowser(cmd.Cmd):
    intro = "Welcome to M.Bot!"
    prompt = "EZID: "

    def __init__(self, username, password, *args, **kwargs):
        self._usr = username
        self._pass = password
        self._devtools = kwargs.pop("devtools", False)
        self._width = kwargs.pop("width", DEFAULT_WIDTH)
        self._height = kwargs.pop("height", DEFAULT_HEIGHT)
        self._base_url = kwargs.pop("url", EZID_URL)
        self._browser = None
        self._page = None
        super().__init__(*args, **kwargs)
        self._adv_search = ADV_SEARCH_BLANK
        self._loop = asyncio.get_event_loop()
        logging.info(self._usr)

    def _tokenize(self, inpt):
        res = list(
            csv.reader(
                [
                    inpt,
                ],
                delimiter=" ",
            )
        )
        if len(res) < 1:
            return []
        return res[0]

    async def _initialize(self):
        self._browser = await launch(
            {
                "headless": False,
                "devtools": self._devtools,
                "args": [f"--window-size={self._width},{self._height+74}"],
            }
        )
        self._page = await self._browser.newPage()
        await self._page.setViewport({"width": self._width, "height": self._height})
        await self._page.goto(f"{EZID_URL}/")

    async def _waitForNavigation(self, timeout=DEFAULT_TIMEOUT):
        try:
            await self._page.waitForNavigation({"timeout": timeout})
        except pyppeteer.errors.TimeoutError as e1:
            logging.info(e1)

    async def _elementText(self, selector, timeout=DEFAULT_TIMEOUT):
        try:
            ele = await self._page.querySelector(selector)
            return await self._page.evaluate(f"(element) => element.textContent", ele)
        except pyppeteer.errors.TimeoutError as e1:
            logging.info(e1)
        return None

    async def navigateTo(self, url, timeout=DEFAULT_TIMEOUT):
        try:
            await self._page.goto(url)
            await self._waitForNavigation(timeout=timeout)
        except Exception as e:
            logging.info(e)

    async def _doclick(self, selector, timeout=DEFAULT_TIMEOUT):
        try:
            await asyncio.wait(
                [
                    asyncio.create_task(
                        self._page.evaluate(
                            "(_ele) => _ele.click()",
                            await self._page.querySelector(selector),
                        )
                    ),
                    asyncio.create_task(self._waitForNavigation(timeout=timeout)),
                ]
            )
        except Exception as e:
            logging.error(e)

    async def _doinput(self, selector, input_str):
        try:
            await asyncio.wait(
                [
                    asyncio.create_task(
                        self._page.evaluate(
                            f"(_ele) => _ele.value='{input_str}'",
                            await self._page.querySelector(selector),
                        )
                    ),
                ]
            )
            return True
        except Exception as e:
            logging.error(e)
        return False

    async def login(self, username, password, timeout=DEFAULT_TIMEOUT):
        await asyncio.wait(
            [
                asyncio.create_task(self._page.waitForNavigation()),
                asyncio.create_task(self._page.goto(f"{EZID_URL}/")),
            ]
        )

        _dlg = await self._page.querySelector("#js-login-modal")
        if _dlg is None:
            L.error("Can't get login dialog!")
            return False
        await self._page.evaluate('(_dlg) => _dlg.style.display = "block"', _dlg)
        await self._doinput("#username", username)
        await self._doinput("#password", password)
        await self._doclick("#login")
        success = False
        try:
            _test = await self._page.waitForSelector(
                "div.login-menu__container", {"timeout": timeout}
            )
            success = True
        except Exception as e:
            L.error(e)
        return success

    async def logout(self, timeout=DEFAULT_TIMEOUT):
        _button = await self._page.querySelector(
            "#js-header__nav > div > form > button"
        )
        if _button is None:
            return False
        await self._page.evaluate("(_button) => _button.click()", _button)
        success = True
        try:
            # #js-header__loginout-button
            _test = await self._page.waitForSelector(
                "#js-header__loginout-button", {"timeout": timeout}
            )
            print(_test)
            success = False
        except pyppeteer.errors.TimeoutError as e1:
            pass
        except Exception as e:
            L.error(e)
        return success

    async def runScript(self, script, timeout=DEFAULT_TIMEOUT):
        return await self._page.evaluate(script, timeout=timeout)

    async def basicSearch(self, qry_str, timeout=DEFAULT_TIMEOUT):
        await self._page.goto(f"{EZID_URL}/search")
        await self._doinput("#search__simple-label", qry_str)
        await self._doclick(
            "#search-form > div.search__simple > button", timeout=timeout
        )
        return await self._elementText("body > div.customize-table > form > h2")

    async def create(self, id_type, location, who, what, when):
        await self._page.goto(f"{EZID_URL}/")
        await self._doinput("#target", location)
        await self._doinput("#erc\.who", who)
        await self._doinput("#erc\.what", what)
        await self._doinput("#erc\.when", when)
        await self._doclick(
            "#create_form > div.fieldset-stacked.fieldset__top-border.home__fieldset > div.row > div.col-md-2.home__create-button > button"
        )
        # body > div.container.vertical-buffer-20 > div:nth-child(3) > div.col-md-8 > div > div.col-md-8.vertical-buffer-bot-md > strong
        result = await self._elementText(
            "body > div.container.vertical-buffer-20 > div:nth-child(3) > div.col-md-8 > div > div.col-md-8.vertical-buffer-bot-md > strong"
        )
        return result

    def preloop(self) -> None:
        self._loop.run_until_complete(self._initialize())

    def postloop(self) -> None:
        print("Bye!")
        self._loop.run_until_complete(self._browser.close())
        self._loop.close()

    def printOk(self, v):
        if v:
            print("OK")
            return
        print("Failed")

    def do_click(self, arg):
        """click SELECTOR
        Emulate a click on an element
        """
        print(f"Selector = {arg}")
        res = self._loop.run_until_complete(self._doclick(arg))
        self.printOk(res)

    def do_input(self, arg):
        """input SELECTOR VALUE
        Set value of the input at SELECTOR to VALUE
        """
        inp = self._tokenize(arg)
        if len(inp) != 2:
            L.error('Expecting "selector" "input"')
            return
        res = self._loop.run_until_complete(self._doinput(*inp))
        self.printOk(res)

    def do_login(self, arg):
        """login
        Login using user name and the password provided at startup.
        """
        res = self._loop.run_until_complete(self.login(self._usr, self._pass))
        self.printOk(res)

    def do_logout(self, arg):
        """logout
        Logout
        """
        res = self._loop.run_until_complete(self.logout())
        self.printOk(res)

    def do_sparam(self, arg):
        """sparam [KEY [VALUE]]
        Set / get search parameter"""
        inp = self._tokenize(arg)
        if len(inp) == 0:
            print(json.dumps(self._adv_search, indent=2))
            return
        if not inp[0] in list(self._adv_search.keys()):
            L.error("Unknown search key: %s", inp[0])
            return
        if len(inp) > 1:
            self._adv_search[inp[0]] = inp[1]
        print(f"{inp[0]} : {self._adv_search.get(inp[0], None)}")

    def do_search(self, arg):
        """search TERM
        Run a simple search for TERM
        """
        if len(arg) < 1:
            print(f"Search needs a term")
            return
        print(f"Query for: '{arg}'")
        res = self._loop.run_until_complete(self.basicSearch(arg))
        print(res)

    def do_user(self, arg):
        """user [USERNAME]
        Get or set the username used to login
        """
        inp = self._tokenize(arg)
        if len(inp) == 1:
            self._usr = inp[0]
        print(self._usr)

    def do_url(self, arg):
        """url [URL]
        Get / set the service URL
        """
        inp = self._tokenize(arg)
        if len(inp) == 1:
            self._base_url = inp[0]
            self._loop.run_until_complete(self.navigateTo(self._base_url))
        print(self._base_url)

    def do_create(self, arg):
        """ """
        id_type = "ARK"
        location = "https://example.net/"
        who = "Maria Bot"
        what = "mbot test"
        when = datetimeToJsonStr(dtnow())
        if len(arg) > 0:
            inp = self._tokenize(arg)
        res = self._loop.run_until_complete(
            self.create(id_type, location, who, what, when)
        )
        res = res.lstrip("*").strip()
        print(f"Identifier = {res}")

    def do_script(self, arg):
        """script SCRIPT
        Execute the provided script
        """
        _script = arg
        res = self._loop.run_until_complete(self.runScript(_script))
        print(res)

    def do_exit(self, arg):
        "Exit from MariaBot"
        return True

    def do_EOF(self, arg):
        "Exit from MariaBot"
        return True


@click.command()
@click.option("--password", default=lambda: os.environ.get("EZID_PASS", ""))
@click.option("--user", default=lambda: os.environ.get("EZID_USER", ""))
@click.option("--devtools", is_flag=True, help="Launch wih devtools")
@click.option("--width", default=DEFAULT_WIDTH, help="Browser window width in pixels")
@click.option("--height", default=DEFAULT_HEIGHT, help="Browser window height in pixels")
@click.option("--url", default=EZID_URL, help="EZID Service URL to use")
def doShell(user, password, devtools, width, height, url):
    ezid = EZBrowser(
        user, password, devtools=devtools, width=width, height=height, url=url
    )
    ezid.cmdloop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    doShell()
