"""
Custom Module Extension Example

Shows how to build custom AIMON modules for specific use cases.
"""

import asyncio
from aimon.core.base_module import BaseModule
from aimon.core.runtime import get_runtime
from aimon import AIMON


class EmailFinderModule(BaseModule):
    """
    Custom module that finds email addresses in crawled content.
    
    Subscribes to page_crawled events and extracts emails.
    """
    
    async def _initialize_impl(self):
        """Initialize email finder module."""
        self.found_emails = []
        await self.emit_event("email_finder_ready")
    
    async def _subscribe_to_events(self):
        """Subscribe to page crawled events."""
        await self.subscribe_event("page_crawled", self._on_page_crawled)
    
    async def _shutdown_impl(self):
        """Shutdown the module."""
        pass
    
    async def _on_page_crawled(self, **data):
        """Handle page_crawled event."""
        page = data.get("page", {})
        content = page.get("content", "")
        
        # Simple email extraction (in production, use regex)
        emails = [
            "admin@example.com",
            "support@example.org"
        ]
        
        self.found_emails.extend(emails)
        
        # Emit event for other modules
        await self.emit_event("emails_found", 
                             emails=emails,
                             source_id=page.get("source_id"))
    
    def get_found_emails(self):
        """Get all found emails."""
        return self.found_emails


class NotificationModule(BaseModule):
    """
    Custom module that sends notifications based on emails found.
    """
    
    async def _initialize_impl(self):
        """Initialize notification module."""
        self.notifications_sent = 0
    
    async def _subscribe_to_events(self):
        """Subscribe to emails_found events."""
        await self.subscribe_event("emails_found", self._on_emails_found)
    
    async def _shutdown_impl(self):
        """Shutdown the module."""
        pass
    
    async def _on_emails_found(self, **data):
        """Handle emails_found event."""
        emails = data.get("emails", [])
        source_id = data.get("source_id", "unknown")
        
        for email in emails:
            # Simulate sending notification
            self.notifications_sent += 1
    
    def get_notification_count(self):
        """Get count of notifications sent."""
        return self.notifications_sent


async def main():
    """Run custom module example."""
    print("[*] Custom Module Extension Example")
    
    # Create AIMON framework
    async with AIMON() as framework:
        # Get runtime
        runtime = framework.runtime
        
        # Register custom modules
        print("[*] Registering custom modules...")
        
        email_finder = EmailFinderModule("email_finder")
        notification = NotificationModule("notifications")
        
        await runtime.register_module("email_finder", email_finder)
        await runtime.register_module("notifications", notification)
        
        print("[+] Custom modules registered")
        
        # Search and let modules process
        print("[*] Searching for sources...")
        sources = await framework.search_sources("document leak")
        
        # Give modules time to process
        await asyncio.sleep(1)
        
        # Get results from custom modules
        print(f"\n[*] Found {len(email_finder.found_emails)} emails")
        print(f"[*] Sent {notification.get_notification_count()} notifications")
        
        print(f"\n[+] Custom module example complete")


if __name__ == "__main__":
    asyncio.run(main())
