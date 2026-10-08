"""Wellfound agent workflow definitions.

This module contains the Temporal workflow logic that coordinates the
sequence of browser activities required to automate the Wellfound agent,
including user login and search filter configuration.
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from wellfound_agent.workflows.activities import (
        apply_filters_activity,
        login_user_activity,
    )


@workflow.defn
class WellfoundAgentWorkflow:
    """Workflow for automating the Wellfound job search process.

    This workflow orchestrates the browser activities to ensure the user
    is authenticated and that the correct job filters are applied
    sequentially.
    """

    @workflow.run
    async def run(self) -> dict[str, str]:
        """Execute the Wellfound agent sequence.

        Coordinates the login and filter activities with a defined
        retry policy and timeout.

        Returns
        -------
        dict[str, str]
            A dictionary containing the final URLs reached after
            the login and filter activities.
        """
        # Define a retry policy for the activities
        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=5),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=2,
        )

        # Execute the activities with the defined retry policy
        login_result = await workflow.execute_activity(
            login_user_activity,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(minutes=2),
        )

        filter_result = await workflow.execute_activity(
            apply_filters_activity,
            retry_policy=retry_policy,
            start_to_close_timeout=timedelta(minutes=2),
        )

        return {
            "login_result": login_result.url,
            "filter_result": filter_result.url,
        }
