import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(autouse=True)
def setup(page: Page):
    # Login before each test
    page.goto("/login")
    page.fill("input[name='username']", "Bossm")
    page.fill("input[name='password']", "Bossm143")
    page.click("button[type='submit']")
    page.wait_for_url("/chat")

def test_responsive_design(page: Page):
    # Test desktop view
    page.set_viewport_size({"width": 1280, "height": 800})
    page.screenshot(path="test-artifacts/desktop-view.png")
    
    # Verify sidebar is visible
    expect(page.locator(".contacts-sidebar")).to_be_visible()
    
    # Test tablet view
    page.set_viewport_size({"width": 768, "height": 1024})
    page.screenshot(path="test-artifacts/tablet-view.png")
    
    # Test mobile view
    page.set_viewport_size({"width": 375, "height": 812})
    page.screenshot(path="test-artifacts/mobile-view.png")
    
    # Verify hamburger menu appears
    expect(page.locator(".hamburger-btn")).to_be_visible()
    
    # Test sidebar toggle on mobile
    page.click(".hamburger-btn")
    expect(page.locator(".contacts-sidebar")).to_have_class("show")
    page.screenshot(path="test-artifacts/mobile-sidebar-open.png")

def test_chat_navigation(page: Page):
    # Click through different chats
    contacts = [".contact-item >> text=Jam", ".contact-item >> text=Buboy", ".contact-item >> text=Ruel"]
    
    for contact in contacts:
        page.click(contact)
        expect(page.locator(".chat-header")).to_be_visible()
        page.screenshot(path=f"test-artifacts/chat-{contact.split('=')[1]}.png")

def test_dark_theme(page: Page):
    # Verify dark theme elements
    expect(page.locator("html")).to_have_attribute("data-bs-theme", "dark")
    page.screenshot(path="test-artifacts/dark-theme.png")
