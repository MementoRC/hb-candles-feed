"""
Project management tool integration.

This module provides integration with external project management tools
for task tracking, milestone management, and progress synchronization.
"""

import asyncio
import hashlib
import hmac
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

import aiohttp
from aiohttp import web

from candles_feed.core.protocols import Logger


class TaskStatus(Enum):
    """Standard task status values."""

    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    DONE = "done"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"


class TaskPriority(Enum):
    """Standard task priority values."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Task:
    """Represents a task in the project management system."""

    id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: str | None = None
    milestone: str | None = None
    labels: list[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.labels is None:
            self.labels = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class Milestone:
    """Represents a milestone in the project management system."""

    id: str
    title: str
    description: str
    due_date: str | None = None
    progress: float = 0.0  # 0.0 to 1.0
    status: str = "active"
    metadata: dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProjectManagementConfig:
    """Configuration for project management integration."""

    webhook_enabled: bool = True
    webhook_port: int = 8081
    webhook_path: str = "/webhook/project-management"
    webhook_secret: str | None = None

    # External project management tool configurations
    github_projects_enabled: bool = False
    github_token: str | None = None
    github_org: str | None = None
    github_project_id: str | None = None

    jira_enabled: bool = False
    jira_url: str | None = None
    jira_username: str | None = None
    jira_api_token: str | None = None
    jira_project_key: str | None = None

    # Synchronization settings
    auto_sync_enabled: bool = True
    sync_interval_seconds: float = 300.0  # 5 minutes

    # Task mapping configuration
    status_mapping: dict[str, TaskStatus] = None
    priority_mapping: dict[str, TaskPriority] = None

    def __post_init__(self):
        """Initialize default mappings."""
        if self.status_mapping is None:
            self.status_mapping = {
                "open": TaskStatus.PENDING,
                "in_progress": TaskStatus.IN_PROGRESS,
                "closed": TaskStatus.DONE,
                "cancelled": TaskStatus.CANCELLED,
                "blocked": TaskStatus.BLOCKED,
            }

        if self.priority_mapping is None:
            self.priority_mapping = {
                "low": TaskPriority.LOW,
                "medium": TaskPriority.MEDIUM,
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL,
            }


class GitHubProjectsIntegration:
    """Integration with GitHub Projects (v2)."""

    def __init__(self, config: ProjectManagementConfig, logger: Logger | None = None):
        """
        Initialize GitHub Projects integration.

        :param config: Project management configuration
        :param logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)

    async def sync_tasks(self) -> list[Task]:
        """
        Sync tasks from GitHub Projects.

        :return: List of synchronized tasks
        """
        if not self.config.github_projects_enabled:
            return []

        # This is a simplified example - GitHub Projects v2 API is complex
        # In practice, you would use GraphQL queries to fetch project data

        tasks = []
        try:
            headers = {
                "Authorization": f"Bearer {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Example: Fetch issues from a repository as tasks
            # This would need to be adapted based on your GitHub Projects setup
            url = f"https://api.github.com/repos/{self.config.github_org}/issues"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        issues = await response.json()

                        for issue in issues:
                            # Map GitHub issue to Task
                            status = TaskStatus.PENDING
                            if issue.get("state") == "closed":
                                status = TaskStatus.DONE

                            priority = TaskPriority.MEDIUM
                            for label in issue.get("labels", []):
                                label_name = label.get("name", "").lower()
                                if "high" in label_name or "urgent" in label_name:
                                    priority = TaskPriority.HIGH
                                elif "low" in label_name:
                                    priority = TaskPriority.LOW

                            task = Task(
                                id=str(issue["number"]),
                                title=issue["title"],
                                description=issue.get("body", ""),
                                status=status,
                                priority=priority,
                                assignee=issue.get("assignee", {}).get("login")
                                if issue.get("assignee")
                                else None,
                                labels=[label["name"] for label in issue.get("labels", [])],
                                metadata={
                                    "github_url": issue["html_url"],
                                    "created_at": issue["created_at"],
                                    "updated_at": issue["updated_at"],
                                },
                            )
                            tasks.append(task)

                        self.logger.debug(f"Synced {len(tasks)} tasks from GitHub")
                    else:
                        self.logger.error(f"Failed to sync GitHub tasks: {response.status}")

        except Exception as e:
            self.logger.error(f"Error syncing GitHub tasks: {e}")

        return tasks

    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """
        Update task status in GitHub.

        :param task_id: Task identifier
        :param status: New task status
        :return: True if updated successfully
        """
        if not self.config.github_projects_enabled:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.config.github_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Example: Update issue state
            url = f"https://api.github.com/repos/{self.config.github_org}/issues/{task_id}"

            # Map TaskStatus to GitHub issue state
            github_state = "open"
            if status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
                github_state = "closed"

            data = {"state": github_state}

            async with aiohttp.ClientSession() as session:
                async with session.patch(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        self.logger.debug(f"Updated GitHub task {task_id} status to {status.value}")
                        return True
                    else:
                        self.logger.error(
                            f"Failed to update GitHub task {task_id}: {response.status}"
                        )
                        return False

        except Exception as e:
            self.logger.error(f"Error updating GitHub task {task_id}: {e}")
            return False


class WebhookHandler:
    """Handles incoming webhooks from project management tools."""

    def __init__(
        self,
        config: ProjectManagementConfig,
        task_update_callback: Callable[[Task], None] | None = None,
        logger: Logger | None = None,
    ):
        """
        Initialize webhook handler.

        :param config: Project management configuration
        :param task_update_callback: Callback function for task updates
        :param logger: Logger instance
        """
        self.config = config
        self.task_update_callback = task_update_callback
        self.logger = logger or logging.getLogger(__name__)
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    def _verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature for security."""
        if not self.config.webhook_secret:
            return True  # Skip verification if no secret configured

        expected_signature = hmac.new(
            self.config.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(f"sha256={expected_signature}", signature)

    async def _webhook_handler(self, request: web.Request) -> web.Response:
        """Handle incoming webhook requests."""
        try:
            # Verify signature if secret is configured
            signature = request.headers.get("X-Hub-Signature-256", "")
            payload = await request.read()

            if not self._verify_webhook_signature(payload, signature):
                self.logger.warning("Invalid webhook signature")
                return web.Response(status=401, text="Invalid signature")

            # Parse webhook payload
            data = json.loads(payload.decode())
            event_type = request.headers.get("X-GitHub-Event", "unknown")

            # Process different types of webhook events
            if event_type == "issues":
                await self._handle_issue_event(data)
            elif event_type == "project_card":
                await self._handle_project_card_event(data)
            else:
                self.logger.debug(f"Unhandled webhook event type: {event_type}")

            return web.Response(status=200, text="OK")

        except Exception as e:
            self.logger.error(f"Error handling webhook: {e}")
            return web.Response(status=500, text="Internal server error")

    async def _handle_issue_event(self, data: dict[str, Any]) -> None:
        """Handle GitHub issue webhook events."""
        action = data.get("action")
        issue = data.get("issue", {})

        if action in ["opened", "edited", "closed", "reopened"]:
            # Convert issue to Task
            status = TaskStatus.PENDING
            if issue.get("state") == "closed":
                status = TaskStatus.DONE

            task = Task(
                id=str(issue["number"]),
                title=issue["title"],
                description=issue.get("body", ""),
                status=status,
                priority=TaskPriority.MEDIUM,  # Default priority
                assignee=issue.get("assignee", {}).get("login") if issue.get("assignee") else None,
                labels=[label["name"] for label in issue.get("labels", [])],
                metadata={
                    "github_url": issue["html_url"],
                    "action": action,
                    "updated_at": issue["updated_at"],
                },
            )

            # Call update callback if configured
            if self.task_update_callback:
                self.task_update_callback(task)

            self.logger.debug(f"Processed GitHub issue webhook: {action} on #{issue['number']}")

    async def _handle_project_card_event(self, data: dict[str, Any]) -> None:
        """Handle GitHub project card webhook events."""
        action = data.get("action")
        # card = data.get("project_card", {})  # Available for future implementation

        self.logger.debug(f"Received project card event: {action}")
        # Implement project card handling based on your needs

    async def start(self) -> None:
        """Start the webhook server."""
        if not self.config.webhook_enabled:
            self.logger.debug("Webhook server disabled")
            return

        try:
            self._app = web.Application()
            self._app.router.add_post(self.config.webhook_path, self._webhook_handler)

            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            site = web.TCPSite(self._runner, "0.0.0.0", self.config.webhook_port)
            await site.start()

            self.logger.info(
                f"Project management webhook server started on port {self.config.webhook_port} "
                f"path {self.config.webhook_path}"
            )
        except Exception as e:
            self.logger.error(f"Failed to start webhook server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
        self._app = None
        self.logger.info("Project management webhook server stopped")


class ProjectManagementIntegration:
    """Main class for project management tool integration."""

    def __init__(self, config: ProjectManagementConfig | None = None, logger: Logger | None = None):
        """
        Initialize project management integration.

        :param config: Integration configuration
        :param logger: Logger instance
        """
        self.config = config or ProjectManagementConfig()
        self.logger = logger or logging.getLogger(__name__)

        self.github_integration = GitHubProjectsIntegration(self.config, logger)
        self.webhook_handler = WebhookHandler(
            self.config, task_update_callback=self._handle_task_update, logger=logger
        )

        self._sync_task: asyncio.Task | None = None
        self._tasks_cache: dict[str, Task] = {}

    def _handle_task_update(self, task: Task) -> None:
        """Handle task updates from webhooks."""
        self._tasks_cache[task.id] = task
        self.logger.debug(f"Updated task cache: {task.id} - {task.title}")

    async def _sync_tasks_periodically(self) -> None:
        """Background task to sync tasks periodically."""
        while True:
            try:
                if self.config.auto_sync_enabled:
                    tasks = await self.github_integration.sync_tasks()

                    # Update cache with synced tasks
                    for task in tasks:
                        self._tasks_cache[task.id] = task

                    self.logger.debug(f"Periodic task sync completed: {len(tasks)} tasks")

                await asyncio.sleep(self.config.sync_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic task sync: {e}")
                await asyncio.sleep(self.config.sync_interval_seconds)

    async def get_tasks(self) -> list[Task]:
        """
        Get all tasks from cache or sync from external systems.

        :return: List of tasks
        """
        if not self._tasks_cache and self.config.auto_sync_enabled:
            # Perform initial sync if cache is empty
            tasks = await self.github_integration.sync_tasks()
            for task in tasks:
                self._tasks_cache[task.id] = task

        return list(self._tasks_cache.values())

    async def get_task(self, task_id: str) -> Task | None:
        """
        Get a specific task by ID.

        :param task_id: Task identifier
        :return: Task instance or None if not found
        """
        return self._tasks_cache.get(task_id)

    async def update_task_status(self, task_id: str, status: TaskStatus) -> bool:
        """
        Update task status in external systems and cache.

        :param task_id: Task identifier
        :param status: New task status
        :return: True if updated successfully
        """
        success = False

        # Update in GitHub if enabled
        if self.config.github_projects_enabled:
            success = await self.github_integration.update_task_status(task_id, status)

        # Update local cache if external update succeeded or if no external system
        if success or not self.config.github_projects_enabled:
            task = self._tasks_cache.get(task_id)
            if task:
                task.status = status
                self._tasks_cache[task_id] = task
                success = True

        return success

    async def start(self) -> None:
        """Start all project management integration components."""
        try:
            await self.webhook_handler.start()

            if self.config.auto_sync_enabled:
                self._sync_task = asyncio.create_task(self._sync_tasks_periodically())

            self.logger.info("Project management integration started")

        except Exception as e:
            self.logger.error(f"Failed to start project management integration: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop all project management integration components."""
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
            self._sync_task = None

        await self.webhook_handler.stop()
        self.logger.info("Project management integration stopped")
