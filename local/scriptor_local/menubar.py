"""macOS menu bar app for Scriptor Local."""
import rumps
import subprocess
import threading
import webbrowser
import sys
from pathlib import Path

from .config import config


class ScriptorLocalApp(rumps.App):
    """Menu bar application for Scriptor Local."""

    def __init__(self):
        super().__init__(
            "Scriptor",
            icon=None,  # Will use text if no icon
            quit_button=None  # We'll add our own
        )
        self.server_process = None
        self.server_running = False

        # Build menu
        self.menu = [
            rumps.MenuItem("Start Server", callback=self.toggle_server),
            None,  # Separator
            rumps.MenuItem("Show Token", callback=self.show_token),
            rumps.MenuItem("Copy Token", callback=self.copy_token),
            None,
            rumps.MenuItem("Open Storage Folder", callback=self.open_storage),
            rumps.MenuItem("Open API Docs", callback=self.open_docs),
            None,
            rumps.MenuItem(f"Port: {config.server_port}"),
            None,
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]

        # Update status
        self._update_status()

    def _update_status(self):
        """Update menu items based on server status."""
        if self.server_running:
            self.title = "📚"  # Running indicator
            self.menu["Start Server"].title = "Stop Server"
        else:
            self.title = "📕"  # Stopped indicator
            self.menu["Start Server"].title = "Start Server"

    def toggle_server(self, sender):
        """Start or stop the server."""
        if self.server_running:
            self.stop_server()
        else:
            self.start_server()
        self._update_status()

    def start_server(self):
        """Start the FastAPI server in a subprocess."""
        if self.server_running:
            return

        def run():
            try:
                # Run uvicorn directly
                import uvicorn
                uvicorn.run(
                    "scriptor_local.app:app",
                    host="127.0.0.1",
                    port=config.server_port,
                    log_level="info"
                )
            except Exception as e:
                rumps.notification(
                    "Scriptor Local",
                    "Server Error",
                    str(e)
                )
                self.server_running = False
                self._update_status()

        self.server_thread = threading.Thread(target=run, daemon=True)
        self.server_thread.start()
        self.server_running = True

        rumps.notification(
            "Scriptor Local",
            "Server Started",
            f"Running on http://127.0.0.1:{config.server_port}"
        )

    def stop_server(self):
        """Stop the server (note: threads can't be cleanly stopped, app restart needed)."""
        rumps.notification(
            "Scriptor Local",
            "Restart Required",
            "Please quit and restart the app to fully stop the server."
        )

    def show_token(self, sender):
        """Show the auth token in a dialog."""
        rumps.alert(
            title="Scriptor Local Token",
            message=f"Your pairing token:\n\n{config.auth_token}\n\nCopy this to the Chrome extension to pair.",
            ok="OK"
        )

    def copy_token(self, sender):
        """Copy the auth token to clipboard."""
        subprocess.run(
            ["pbcopy"],
            input=config.auth_token.encode(),
            check=True
        )
        rumps.notification(
            "Scriptor Local",
            "Token Copied",
            "Auth token copied to clipboard"
        )

    def open_storage(self, sender):
        """Open the storage folder in Finder."""
        subprocess.run(["open", str(config.storage_dir)])

    def open_docs(self, sender):
        """Open API documentation in browser."""
        if self.server_running:
            webbrowser.open(f"http://127.0.0.1:{config.server_port}/docs")
        else:
            rumps.alert(
                "Server Not Running",
                "Start the server first to access API docs."
            )

    def quit_app(self, sender):
        """Quit the application."""
        rumps.quit_application()


def run_menubar():
    """Run the menu bar application."""
    app = ScriptorLocalApp()

    # Auto-start server if configured
    if config.auto_start_server:
        app.start_server()

    app.run()


if __name__ == "__main__":
    run_menubar()
