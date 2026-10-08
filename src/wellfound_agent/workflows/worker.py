"""Worker entry point for the Wellfound Agent.

This module initializes the connection to the Temporal server and starts
the worker responsible for executing the WellfoundAgentWorkflow and its
associated browser activities.
"""

from temporalio.client import Client
from temporalio.worker import Worker

from wellfound_agent.config.settings import get_settings
from wellfound_agent.workflows.activities import apply_filters_activity, login_user_activity
from wellfound_agent.workflows.definitions import WellfoundAgentWorkflow


async def main() -> None:
    """Entry point to start the Temporal worker.

    Connects to the Temporal cluster using the configured host and namespace,
    then initializes and runs a Worker registered with the
    WellfoundAgentWorkflow and required browser activities.
    """
    # Initialize the settings
    settings = get_settings()

    # Connect to the Temporal server
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    # Create a worker that listens to the specified task queue
    # and registers the workflow and activities
    worker = Worker(
        client=client,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
        workflows=[WellfoundAgentWorkflow],
        activities=[login_user_activity, apply_filters_activity],
    )

    await worker.run()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
