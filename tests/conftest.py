import pytest
import typing

@pytest.fixture(scope="session")
def ezid_base():
    return "http://localhost:18880"
    #return "https://ezid-stg.cdlib.org"

@pytest.fixture(scope="session")
def executable_path(executable_path):
    #print("EXECUTABLE_PATH: ", executable_path)
    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    #if executable_path is None:
    #    return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    #return executable_path

@pytest.fixture(scope="session")
def args(args) -> typing.List[str]:
    return args + [
        ]
