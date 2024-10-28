import pytest
import os
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {
            "width": 1280,
            "height": 720,
        },
        "record_video_dir": "test-videos",
    }

@pytest.fixture(autouse=True)
def setup(page):
    # Create directories for test artifacts
    os.makedirs("test-screenshots", exist_ok=True)
    os.makedirs("test-videos", exist_ok=True)
    
    # Inject performance monitoring
    page.on("console", lambda msg: print(f"Browser console: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"Page error: {exc}"))
    
    def handle_route(route):
        timing = {
            "startTime": page.evaluate("performance.now()"),
            "endTime": None,
            "duration": None
        }
        
        def handle_response(response):
            timing["endTime"] = page.evaluate("performance.now()")
            timing["duration"] = timing["endTime"] - timing["startTime"]
            print(f"Request to {route.request.url} took {timing['duration']}ms")
        
        route.continue_()
        route.request.response().then(handle_response)
    
    page.route("**/*", handle_route)
    
    yield page
