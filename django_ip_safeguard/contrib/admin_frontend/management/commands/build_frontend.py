import os
import subprocess
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Build the admin frontend Vue.js application"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Run in watch mode for development",
        )

    def handle(self, *args, **options):
        frontend_dir = Path(__file__).resolve().parent.parent.parent / "contrib" / "admin_frontend"

        if not frontend_dir.exists():
            self.stderr.write(self.style.ERROR(f"Frontend directory not found: {frontend_dir}"))
            return

        self.stdout.write(f"Building frontend in {frontend_dir}...")

        try:
            subprocess.run(
                ["npm", "install"],
                cwd=frontend_dir,
                check=True,
                capture_output=True,
            )

            build_cmd = ["npm", "run", "build"]
            if options["watch"]:
                build_cmd.append("--watch")

            result = subprocess.run(
                build_cmd,
                cwd=frontend_dir,
                check=True,
            )

            self.stdout.write(self.style.SUCCESS("Frontend build completed successfully!"))

        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"Frontend build failed: {e}"))
            raise
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR("npm not found. Please install Node.js and npm."))
