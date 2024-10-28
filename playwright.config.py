from playwright.sync_api import Playwright

def pytest_configure(config):
    config.option.base_url = "http://localhost:5000"

def pytest_runtest_setup(item):
    # Setup code that runs before each test
    pass
