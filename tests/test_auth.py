import pytest
from playwright.sync_api import Page, expect

def test_login_success(page: Page):
    # Navigate to login page
    page.goto("/login")
    
    # Fill in valid credentials
    page.fill("input[name='username']", "Bossm")
    page.fill("input[name='password']", "Bossm143")
    
    # Take screenshot before login
    page.screenshot(path="test-artifacts/login-form.png")
    
    # Submit login form
    page.click("button[type='submit']")
    
    # Verify redirect to chat page
    expect(page).to_have_url("/chat")
    
    # Take screenshot after successful login
    page.screenshot(path="test-artifacts/after-login.png")

def test_login_failure(page: Page):
    # Navigate to login page
    page.goto("/login")
    
    # Fill in invalid credentials
    page.fill("input[name='username']", "invalid")
    page.fill("input[name='password']", "wrong")
    
    # Submit login form
    page.click("button[type='submit']")
    
    # Verify error message
    expect(page.locator(".alert-danger")).to_be_visible()
    
    # Take screenshot of error state
    page.screenshot(path="test-artifacts/login-error.png")

def test_logout(page: Page):
    # First login
    page.goto("/login")
    page.fill("input[name='username']", "Bossm")
    page.fill("input[name='password']", "Bossm143")
    page.click("button[type='submit']")
    
    # Take screenshot before logout
    page.screenshot(path="test-artifacts/before-logout.png")
    
    # Click logout button
    page.click("a:text('Logout')")
    
    # Verify redirect to login page
    expect(page).to_have_url("/login")
    
    # Take screenshot after logout
    page.screenshot(path="test-artifacts/after-logout.png")
