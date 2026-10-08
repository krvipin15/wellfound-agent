"""Workflow trigger module for the Wellfound Agent.

This module provides the client-side logic to initiate and execute the
WellfoundAgentWorkflow on the Temporal server using a unique workflow ID.
"""

import uuid

from temporalio.client import Client

from wellfound_agent.config.settings import get_settings
from wellfound_agent.workflows.definitions import WellfoundAgentWorkflow


async def main() -> None:
    """Entry point to trigger the Wellfound agent workflow.

    Connects to the Temporal cluster, generates a unique workflow ID,
    and schedules the WellfoundAgentWorkflow to run on the configured
    task queue.
    """
    # Initialize the settings
    settings = get_settings()

    # Connect to the Temporal server
    client = await Client.connect(
        settings.TEMPORAL_HOST,
        namespace=settings.TEMPORAL_NAMESPACE,
    )

    # Execute the workflow
    workflow_id = f"wellfound-agent-{uuid.uuid4().hex}"
    await client.execute_workflow(
        WellfoundAgentWorkflow.run,
        id=workflow_id,
        task_queue=settings.TEMPORAL_TASK_QUEUE,
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
