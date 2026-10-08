"""Wellfound browser activities module.

This module defines the Temporal activities responsible for orchestrating
browser-based workflows on Wellfound, such as user authentication and
the application of job search filters.
"""

from dataclasses import dataclass

from temporalio import activity

from wellfound_agent.browser.filter import apply_filters
from wellfound_agent.browser.login import authenticate_user
from wellfound_agent.browser.session import BrowserManager
from wellfound_agent.config.settings import get_settings


@dataclass(frozen=True)
class PageState:
    """Represents the state of the browser page after an activity.

    Attributes
    ----------
    url : str
        The current URL of the browser page.
    """

    url: str


@activity.defn
async def login_user_activity() -> PageState:
    """Temporal activity to authenticate the user on Wellfound.

    Initializes a browser session, executes the login sequence, and
    returns the resulting page state before closing the browser.

    Returns
    -------
    PageState
        The state of the page after a successful login.
    """
    # Initialize the browser
    browser = BrowserManager()

    # Perform the login process
    try:
        page = await browser.get_page()
        await authenticate_user(page)

        return PageState(url=page.url)
    finally:
        await browser.close()


@activity.defn
async def apply_filters_activity() -> PageState:
    """Temporal activity to apply job search filters on Wellfound.

    Navigates to the jobs page using configured settings and applies
    the defined search filters.

    Returns
    -------
    PageState
        The state of the page after filters have been applied.
    """
    # Initialize the browser and get the settings
    settings = get_settings()
    browser = BrowserManager()

    # Perform the filter application process
    try:
        page = await browser.get_page()

        await page.goto(
            settings.JOBS_URL,
            wait_until="domcontentloaded",
            timeout=settings.BROWSER_TIMEOUT_MS,
        )

        await apply_filters(page)

        return PageState(url=page.url)
    finally:
        await browser.close()
