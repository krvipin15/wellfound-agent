"""Browser authentication module for Wellfound.

This module provides the necessary logic to handle user authentication
within the Wellfound platform using Playwright, ensuring that the agent
is correctly logged in before performing further automation tasks.
"""

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from wellfound_agent.config.logger import get_logger
from wellfound_agent.config.settings import get_settings


async def authenticate_user(page: Page) -> None:
    """Authenticate the user account on Wellfound using configured credentials.

    This method handles the end-to-end login flow: navigating to the login page,
    checking for existing sessions, filling in the email and password, and
    verifying that the authentication was successful.

    Parameters
    ----------
    page : Page
        The Playwright Page object representing the browser page to interact with.

    Raises
    ------
    ValueError
        If `USER_EMAIL` or `USER_PASSWORD` are not configured in the settings.
    RuntimeError
        If authentication fails due to an error message on the page or if the
        user remains on the login page after submission.
    """
    # Retrieve settings and logger
    settings = get_settings()
    logger = get_logger()

    # Validate that the necessary credentials are provided
    if not settings.USER_EMAIL or not settings.USER_PASSWORD:
        raise ValueError(
            "USER_EMAIL and USER_PASSWORD must be configured in .env for authentication."
        )

    # Set timeouts for navigation and element interactions
    page.set_default_navigation_timeout(45_000)
    page.set_default_timeout(15_000)

    # Navigate to the login page and check if already logged in
    logger.info("Navigating to Wellfound login page", url=settings.LOGIN_URL)
    try:
        await page.goto(
            settings.LOGIN_URL,
            wait_until="domcontentloaded",
            timeout=30_000,
        )
    except PlaywrightTimeoutError:
        logger.warning(
            "Navigation did not finish within timeout",
            url=page.url,
        )

    # Check the URL after redirects
    if "/login" not in page.url:
        logger.info("Session already valid, user logged in.", url=page.url)
        return

    logger.debug("User is not logged in. Proceeding with authentication.")

    # Locate the email and password input fields on the login page
    logger.debug("Locating login input fields.")
    email = page.locator("input[type='email'], input[name='user[email]'], #user_email").first
    logger.debug("Locating password input field.")
    password = page.locator(
        "input[type='password'], input[name='user[password]'], #user_password"
    ).first

    await email.wait_for(state="visible")
    await password.wait_for(state="visible")

    logger.debug("Filling in login credentials.")
    await email.fill(settings.USER_EMAIL)
    await password.fill(settings.USER_PASSWORD.get_secret_value())

    # Locate the submit button and click it to log in
    logger.debug("Locating the submit button.")
    submit = page.locator("input[type='submit']").first
    await submit.wait_for(state="visible")
    logger.debug("Clicking the submit button.")
    await submit.click()

    # Check for error messages on the login page after submission
    login_error = page.locator("#errorExplanation")
    try:
        await login_error.wait_for(state="visible", timeout=5_000)
        error_text = (await login_error.inner_text()).strip()
        raise RuntimeError(f"Wellfound authentication failed: {error_text}")
    except PlaywrightTimeoutError:
        logger.debug("No login error message appeared.")
        pass

    if "/login" in page.url:
        raise RuntimeError("Login failed without an explicit error message.")

    logger.info("Authentication successful.", url=page.url)
