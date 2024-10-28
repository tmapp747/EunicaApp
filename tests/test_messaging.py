import pytest
from playwright.sync_api import Page, expect
import time

@pytest.fixture(autouse=True)
def setup(page: Page):
    # Login before each test
    page.goto("/login")
    page.fill("input[name='username']", "Bossm")
    page.fill("input[name='password']", "Bossm143")
    page.click("button[type='submit']")
    page.wait_for_url("/chat")

def test_send_text_message(page: Page):
    # Navigate to a chat
    page.click(".contact-item >> text=Jam")
    
    # Take screenshot of empty chat
    page.screenshot(path="test-artifacts/before-message.png")
    
    # Type and send message
    test_message = f"Test message {time.time()}"
    page.fill("#message-input", test_message)
    page.click("button:text('Send')")
    
    # Wait for message to appear
    page.wait_for_selector(f".message:has-text('{test_message}')")
    
    # Take screenshot after sending
    page.screenshot(path="test-artifacts/after-message.png")
    
    # Verify message appears in chat
    expect(page.locator(".message-content").last).to_contain_text(test_message)

def test_file_upload(page: Page):
    # Navigate to a chat
    page.click(".contact-item >> text=Jam")
    
    # Prepare file upload
    with page.expect_file_chooser() as fc_info:
        page.click("label.attach-btn")
    file_chooser = fc_info.value
    
    # Upload test image
    file_chooser.set_files("test-artifacts/before-message.png")
    
    # Take screenshot of upload progress
    page.screenshot(path="test-artifacts/file-upload.png")
    
    # Click send button
    page.click("button:text('Send')")
    
    # Wait for file message to appear
    page.wait_for_selector(".file-attachment")
    
    # Verify file appears in chat
    expect(page.locator(".file-attachment")).to_be_visible()
    
    # Take screenshot after upload
    page.screenshot(path="test-artifacts/after-upload.png")

def test_real_time_updates(page: Page, browser):
    # Open second browser context for receiver
    context2 = browser.new_context()
    page2 = context2.new_page()
    
    # Login as different user in second context
    page2.goto("/login")
    page2.fill("input[name='username']", "Jam")
    page2.fill("input[name='password']", "Jam143")
    page2.click("button[type='submit']")
    
    # Navigate to chat in both contexts
    page.click(".contact-item >> text=Jam")
    page2.click(".contact-item >> text=Bossm")
    
    # Send message from first user
    test_message = f"Real-time test {time.time()}"
    page.fill("#message-input", test_message)
    page.click("button:text('Send')")
    
    # Verify message appears in second context
    page2.wait_for_selector(f".message:has-text('{test_message}')")
    
    # Take screenshots of both contexts
    page.screenshot(path="test-artifacts/sender-view.png")
    page2.screenshot(path="test-artifacts/receiver-view.png")
    
    # Clean up
    context2.close()
