import pytest
from playwright.sync_api import Page, expect
import time

@pytest.fixture(autouse=True)
def setup(page: Page):
    # Navigate to login page
    page.goto("/login")
    # Login with test user
    page.fill("input[name='username']", "Bossm")
    page.fill("input[name='password']", "Bossm143")
    page.click("button[type='submit']")
    # Wait for navigation
    page.wait_for_url("/chat")

def test_search_functionality(page: Page):
    # Click on search input
    page.fill("#message-search", "test message")
    
    # Wait for search results
    search_results = page.wait_for_selector("#search-results")
    expect(search_results).to_be_visible()
    
    # Check if the search results are displayed correctly
    result_items = page.locator(".search-result-item")
    
    # Take a screenshot for visual verification
    page.screenshot(path="test-artifacts/search-results.png")

def test_empty_search(page: Page):
    # Clear search input
    page.fill("#message-search", "")
    
    # Check if search results are hidden
    search_results = page.locator("#search-results")
    expect(search_results).to_have_class("d-none")

def test_search_navigation(page: Page):
    # Search for a message
    page.fill("#message-search", "test message")
    
    # Wait for search results
    page.wait_for_selector("#search-results")
    
    # Click on the first result
    page.click(".search-result-item")
    
    # Verify navigation to chat
    expect(page).to_have_url("/chat/")
