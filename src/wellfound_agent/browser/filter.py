"""Job filter automation module for Wellfound.

This module provides functions to interact with the Wellfound search filter
control panel, allowing for the programmatic setting of job titles,
locations, skills, keywords, and experience levels based on the agent's
configured settings.
"""

from playwright.async_api import Locator, Page

from wellfound_agent.config.logger import get_logger
from wellfound_agent.config.settings import get_settings


async def apply_filters(page: Page) -> None:
    """
    Navigates to the jobs page and applies a comprehensive set of search filters.

    This method ensures the filter modal is open, clears existing filters, and
    sequentially sets job titles, locations, skills, keywords, and experience
    ranges based on the configured `job_filters`.

    Parameters
    ----------
    page : Page
        The Playwright page instance used for browser automation.
    """
    # Retrieve the agent's settings and logger
    settings = get_settings()
    logger = get_logger()
    job_filters = settings.JOB_FILTER

    # Open the filter control panel if not already open
    modal_panel = page.locator('[data-test="SearchBar-FilterControlPanelModal"]')
    if not await modal_panel.is_visible():
        logger.debug("Filter panel not visible, attempting to open it.")
        filters_button = page.locator(
            '[data-test="SearchBar-ToggleFilterControlPanelButton"]'
        ).first
        await filters_button.wait_for(state="visible", timeout=15_000)
        await filters_button.click()
        await modal_panel.wait_for(state="visible", timeout=10_000)

    logger.info("Opened filter control panel.")

    # Clear any existing filters to start fresh
    await _clear_existing_filters(page, modal_panel)

    # Set job titles filter if specified
    await _set_job_titles(modal_panel, job_filters.job_title)
    await _reset_context(modal_panel)

    # Set locations filter if specified
    await _set_locations(modal_panel, job_filters.locations)
    await _reset_context(modal_panel)

    # Set skills filter if specified
    await _set_skills(modal_panel, job_filters.skills)
    await _reset_context(modal_panel)

    # Set include keywords filters if specified
    await _set_include_keywords(modal_panel, job_filters.include_keywords)
    await _reset_context(modal_panel)

    # Set exclude keywords filter if specified
    await _set_exclude_keywords(modal_panel, job_filters.exclude_keywords)
    await _reset_context(modal_panel)

    # Set experience filters if specified
    min_years = job_filters.experience_min_years
    max_years = job_filters.experience_max_years
    if min_years is not None or max_years is not None:
        await _set_experience(
            modal_panel,
            minimum=0 if min_years is None else min_years,
            maximum=10 if max_years is None else max_years,
        )

    # Click the "View results" button to apply all the set filters
    apply_filters_button = modal_panel.get_by_role("button", name="View results")
    await apply_filters_button.wait_for(state="visible", timeout=10_000)
    logger.info("Applying filters.")
    await apply_filters_button.click()


async def _reset_context(modal_panel: Locator) -> None:
    """Reset the context of the filter panel."""
    await modal_panel.get_by_text("Compensation", exact=True).click()


async def _clear_existing_filters(page: Page, modal_panel: Locator) -> None:
    """Remove any currently active filters within the filter modal.

    Parameters
    ----------
    page : Page
        The Playwright page instance.
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    """
    logger = get_logger()

    # Check for and clear any active job type filters
    logger.debug("Checking for active job type filters to clear.")
    clear_single = modal_panel.locator('[data-test="ActiveFilterSummary-FilterButton--jobTypes"]')
    if await clear_single.is_visible():
        await clear_single.click()
        await page.wait_for_timeout(500)
        logger.info("Cleared single job type filter.")

    # Check for and clear all other active filters
    logger.debug("Checking for 'Clear All' button.")
    clear_all = modal_panel.get_by_role("button", name="Clear All")
    if await clear_all.is_visible():
        await clear_all.click()
        await page.wait_for_timeout(500)
        logger.info("Cleared all active filters.")


async def _set_job_titles(modal_panel: Locator, job_titles: list[str] | None) -> None:
    """Clear existing job title selections and inputs new ones from the filter configuration.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    job_titles : list[str] | None
        A list of job titles to set, or None to leave unchanged.
    """
    logger = get_logger()

    # Locate the role wrapper and role button elements in the modal panel
    role_wrapper = modal_panel.locator('[data-test="RoleSelectWrapper"]').first
    await role_wrapper.wait_for(state="visible", timeout=10_000)
    role_button = role_wrapper.locator('[data-test="SearchBar-RoleSelect-FocusButton"]').first
    await role_button.wait_for(state="visible", timeout=10_000)

    # Retrieve the current text from the role button and parse existing roles
    text = (await role_button.inner_text()).strip()
    existing_roles = [role.strip() for role in text.split("•") if role.strip()]

    # If there are existing roles, click the role button to focus and clear them
    if existing_roles:
        await role_button.click()
        await modal_panel.page.wait_for_timeout(300)
        for _ in existing_roles:
            await modal_panel.page.keyboard.press("Backspace")
            await modal_panel.page.wait_for_timeout(150)
        logger.debug("Cleared existing job titles.")

    # If no new job titles are specified, log and exit the function
    if not job_titles:
        logger.debug("No job titles specified in the job filters, skipping job title filter setup.")
        return

    # Input each specified job title into the role input field and confirm with Enter
    for job_title in job_titles:
        logger.debug("Adding job title filter.", job_title=job_title)
        role_input = role_wrapper.locator("input").first
        await role_input.wait_for(state="visible", timeout=10_000)
        await role_input.fill(job_title)
        await modal_panel.page.keyboard.press("Enter")
        await modal_panel.page.wait_for_timeout(300)

    logger.info("Added all job title filters.", job_titles=job_titles)


async def _set_locations(modal_panel: Locator, locations: list[str] | None) -> None:
    """Clear existing location selections and inputs new ones from the filter configuration.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    locations : list[str] | None
        A list of locations to set, or None to leave unchanged.
    """
    logger = get_logger()

    # Locate the location wrapper and button elements in the modal panel
    location_wrapper = modal_panel.locator('div[class*="locationWrapper"]').first
    location_button = location_wrapper.locator("button").first
    await location_button.wait_for(state="visible", timeout=10_000)

    # Retrieve the current text from the location button and parse existing locations
    text = (await location_button.inner_text()).strip()
    existing_locs = [loc.strip() for loc in text.split("•") if loc.strip()]
    if existing_locs:
        await location_button.click()
        await modal_panel.page.wait_for_timeout(300)
        for _ in existing_locs:
            await modal_panel.page.keyboard.press("Backspace")
            await modal_panel.page.wait_for_timeout(150)
        logger.debug("Cleared existing locations.")

    # If no new locations are specified, log and exit the function
    if not locations:
        logger.debug("No locations specified in the job filters, skipping location filter setup.")
        return

    # Input each specified location into the location input field and confirm with Enter
    for loc in locations:
        logger.debug("Adding location filter.", location=loc)
        loc_input = location_wrapper.locator("input").first
        await loc_input.wait_for(state="visible", timeout=10_000)
        await loc_input.fill(loc)
        await modal_panel.page.wait_for_timeout(1000)
        await modal_panel.page.keyboard.press("Enter")
        await modal_panel.page.wait_for_timeout(150)

    logger.info("Added all location filters.", locations=locations)


async def _set_skills(modal_panel: Locator, skills: list[str] | None) -> None:
    """Add a list of skill filters to the search criteria.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    skills : list[str] | None
        A list of skill strings to apply. If None or empty, the step is skipped.
    """
    logger = get_logger()

    # If no skills are provided, log and exit the function
    if not skills:
        logger.debug("No skills specified in the job filters, skipping skills filter setup.")
        return

    # Locate the skills input wrapper and button elements in the modal panel
    skills_wrapper = modal_panel.locator('input[id="skills-input"]').first
    await skills_wrapper.wait_for(state="visible", timeout=10_000)
    for skill in skills:
        logger.debug("Adding skill filter.", skill=skill)
        await skills_wrapper.fill(skill)
        await modal_panel.page.keyboard.press("Enter")
        await modal_panel.page.wait_for_timeout(1000)
        await modal_panel.page.keyboard.press("ArrowDown")
        await modal_panel.page.keyboard.press("Enter")
        await modal_panel.page.wait_for_timeout(150)

    logger.info("Set skills in the modal panel.", skills=skills)


async def _set_include_keywords(modal_panel: Locator, keywords: list[str] | None) -> None:
    """Add a list of keywords that must be included in the job listings.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    keywords : list[str] | None
        A list of keywords to include. If None or empty, the step is skipped.
    """
    logger = get_logger()

    # If no keywords are provided, log and exit the function
    if not keywords:
        logger.debug(
            "No include keywords specified in the job filters, skipping include keywords filter setup."
        )
        return

    # Locate the keywords input field in the modal panel
    wrapper = modal_panel.locator('input[data-test="KeywordsFilterField--keywords--input"]').first
    await wrapper.wait_for(state="visible", timeout=10_000)
    for keyword in keywords:
        logger.debug("Adding to include keyword.", keyword=keyword)
        await wrapper.fill(keyword)
        await wrapper.press("Enter")
        await modal_panel.page.wait_for_timeout(150)

    logger.info("Set include keywords in the modal panel.", keywords=keywords)


async def _set_exclude_keywords(modal_panel: Locator, keywords: list[str] | None) -> None:
    """Add a list of keywords that should exclude jobs from the results.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    keywords : list[str] | None
        A list of keywords to exclude. If None or empty, the step is skipped.
    """
    logger = get_logger()

    # If no keywords are provided, log and exit the function
    if not keywords:
        logger.debug(
            "No exclude keywords specified in the job filters, skipping exclude keywords setup."
        )
        return

    # Locate the exclude keywords input wrapper in the modal panel
    wrapper = modal_panel.locator(
        'input[data-test="KeywordsFilterField--excludedKeywords--input"]'
    ).first
    await wrapper.wait_for(state="visible", timeout=10_000)
    for keyword in keywords:
        logger.debug("Adding exclude keyword.", keyword=keyword)
        await wrapper.fill(keyword)
        await wrapper.press("Enter")
        await modal_panel.page.wait_for_timeout(150)

    logger.info("Set exclude keywords in the modal panel.", keywords=keywords)


async def _set_experience(modal_panel: Locator, minimum: int, maximum: int) -> None:
    """Adjust the experience range slider to the specified minimum and maximum years.

    Parameters
    ----------
    modal_panel : Locator
        The Playwright locator for the filter control panel modal.
    minimum : int
        The minimum years of experience to set.
    maximum : int
        The maximum years of experience to set.

    Raises
    ------
    RuntimeError
        If the experience slider does not contain exactly two handles.
    """
    logger = get_logger()

    # Locate the experience slider handles
    heading = modal_panel.get_by_text("Required experience", exact=True)
    await heading.wait_for(state="visible", timeout=10_000)
    container = heading.locator(
        "xpath=ancestor::div[.//*[contains(@class, 'rheostat-horizontal')]][1]"
    )
    handles = container.locator('[role="slider"]')
    await handles.first.scroll_into_view_if_needed()

    max_handles = 2
    if await handles.count() != max_handles:
        raise RuntimeError("Expected exactly two experience slider handles.")

    # Drag each handle to the specified minimum and maximum values
    for handle, target in ((handles.nth(0), minimum), (handles.nth(1), maximum)):
        await _drag_handle(modal_panel.page, handle, target)

    logger.info("Set experience filter.", minimum=minimum, maximum=maximum)


async def _drag_handle(page: Page, handle: Locator, target: int) -> None:
    """Move a slider handle to a specific numerical value using keyboard arrow keys.

    Parameters
    ----------
    page : Page
        The Playwright page instance.
    handle : Locator
        The locator for the specific slider handle (min or max).
    target : int
        The target value for the `aria-valuenow` attribute.

    Raises
    ------
    RuntimeError
        If the handle does not reach the target value after the operation.
    """
    logger = get_logger()

    # Determine the direction to move the handle
    current_val = await handle.get_attribute("aria-valuenow")
    current = int(current_val or "0")
    key = "ArrowRight" if target > current else "ArrowLeft"
    logger.debug(
        "Moving slider handle.",
        current=current,
        target=target,
        direction="right" if key == "ArrowRight" else "left",
    )

    # Move the handle using keyboard arrow keys
    await handle.focus()
    for _ in range(abs(target - current)):
        await page.keyboard.press(key)
        await page.wait_for_timeout(50)

    # Verify that the handle has reached the target value
    actual_val = await handle.get_attribute("aria-valuenow")
    actual = int(actual_val or "0")
    if actual != target:
        raise RuntimeError(f"Handle (was {current}) ended at {actual}, wanted {target}.")
