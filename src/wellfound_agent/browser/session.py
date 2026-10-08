"""Browser session managing module for Wellfound.

This module provides the BrowserManager class, which manages a persistent
Chromium browser context using Playwright. The manager handles the lifecycle
of the Playwright runtime and the browser context, ensuring that resources are
cleaned up properly on shutdown or in case of errors during initialization.
"""

from playwright.async_api import (
    BrowserContext,
    Error as PlaywrightError,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from wellfound_agent.config.logger import get_logger
from wellfound_agent.config.settings import get_settings


class BrowserManager:
    """Manage a persistent Playwright Chromium browser context.

    The manager owns the Playwright runtime and one persistent Chromium
    context. The context is reused across calls and is shut down cleanly
    when the manager is closed.
    """

    def __init__(self) -> None:
        """Initialize the browser manager."""
        self.settings = get_settings()
        self.logger = get_logger()

        self._playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    async def open(self) -> BrowserContext:
        """Start or return the persistent Chromium browser context.

        Returns
        -------
        BrowserContext
            The initialized persistent Chromium browser context.

        Raises
        ------
        RuntimeError
            If the browser cannot be initialized.
        """
        if self.context is not None:
            self.logger.debug("Returning existing browser context.")
            return self.context

        self.logger.info(
            "Starting Playwright browser session",
            headless=self.settings.HEADLESS_BROWSER,
            user_data_dir=str(self.settings.BROWSER_USER_DATA_DIR.resolve()),
        )

        playwright: Playwright | None = None

        try:
            self.logger.debug("Launching Playwright runtime.")
            playwright = await async_playwright().start()

            self.logger.debug("Launching persistent Chromium context.")
            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.BROWSER_USER_DATA_DIR.resolve()),
                headless=self.settings.HEADLESS_BROWSER,
                viewport={"width": 1920, "height": 1080},
                ignore_https_errors=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )

            context.set_default_timeout(self.settings.BROWSER_TIMEOUT_MS)

            self._playwright = playwright
            self.context = context

            self.logger.info("Browser context initialized successfully.")

            return self.context

        except PlaywrightTimeoutError as exc:
            self.logger.exception(
                "Timed out while starting the Playwright browser.",
            )
            await self._cleanup_failed_startup(playwright)

            raise RuntimeError(
                "Timed out while starting the Playwright browser.",
            ) from exc

        except PlaywrightError as exc:
            self.logger.exception(
                "Playwright failed to initialize the browser.",
            )
            await self._cleanup_failed_startup(playwright)

            raise RuntimeError(
                "Failed to initialize the Playwright browser.",
            ) from exc

        except Exception as exc:
            self.logger.exception(
                "Unexpected error while starting the browser.",
            )
            await self._cleanup_failed_startup(playwright)

            raise RuntimeError(
                "Unexpected error while starting the browser.",
            ) from exc

    async def get_page(self) -> Page:
        """Return the first existing page or create a new page.

        Returns
        -------
        Page
            A page belonging to the persistent browser context.

        Raises
        ------
        RuntimeError
            If the browser context cannot be initialized or a page cannot
            be created.
        """
        context = await self.open()

        try:
            if context.pages:
                self.logger.debug(
                    "Using existing page from context.", page_count=len(context.pages)
                )
                page = context.pages[0]
            else:
                self.logger.debug("No existing pages found. Creating a new page.")
                page = await context.new_page()

            if not page.is_closed():
                try:
                    self.logger.debug("Waiting for DOMContentLoaded.", url=page.url)
                    await page.wait_for_load_state(
                        "domcontentloaded",
                        timeout=self.settings.BROWSER_TIMEOUT_MS,
                    )
                except PlaywrightTimeoutError:
                    self.logger.warning(
                        "Page did not reach DOMContentLoaded before timeout.",
                        url=page.url,
                    )

            self.logger.debug(
                "Page retrieved from browser context.",
                url=page.url,
            )

            return page

        except PlaywrightError as exc:
            self.logger.exception(
                "Playwright failed while retrieving a page.",
            )
            raise RuntimeError(
                "Failed to retrieve a browser page.",
            ) from exc

        except Exception as exc:
            self.logger.exception(
                "Unexpected error while retrieving a browser page.",
            )
            raise RuntimeError(
                "Unexpected error while retrieving a browser page.",
            ) from exc

    async def close(self) -> None:
        """Close the browser context and stop the Playwright runtime.

        Shutdown is idempotent and attempts to clean up all resources even
        when one cleanup operation fails.
        """
        context = self.context
        playwright = self._playwright

        # Set the context and playwright to None before closing to avoid
        # potential re-entrancy issues if close_browser is called again during
        # the closing process.
        self.context = None
        self._playwright = None

        if context is not None:
            self.logger.info("Closing browser context.")

            try:
                await context.close()
                self.logger.debug("Browser context closed.")
            except PlaywrightError:
                self.logger.exception(
                    "Playwright error while closing browser context.",
                )
            except Exception:
                self.logger.exception(
                    "Unexpected error while closing browser context.",
                )

        if playwright is not None:
            self.logger.info("Stopping Playwright.")

            try:
                await playwright.stop()
                self.logger.debug("Playwright runtime stopped.")
            except PlaywrightError:
                self.logger.exception(
                    "Playwright error while stopping Playwright.",
                )
            except Exception:
                self.logger.exception(
                    "Unexpected error while stopping Playwright.",
                )

        self.logger.info("Browser shutdown completed.")

    async def _cleanup_failed_startup(
        self,
        playwright: Playwright | None,
    ) -> None:
        """Clean up Playwright after a failed browser startup.

        Parameters
        ----------
        playwright : Playwright | None
            The Playwright instance to stop. If None, no action is taken.
        """
        if playwright is None:
            return

        try:
            self.logger.debug("Cleaning up Playwright runtime after failure.")
            await playwright.stop()
        except Exception:
            self.logger.exception(
                "Failed to clean up Playwright after startup failure.",
            )
