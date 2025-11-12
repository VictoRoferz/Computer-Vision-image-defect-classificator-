"""Label Studio project initialization script.

This script initializes a Label Studio project with the correct configuration
for PCB defect classification.
"""

import os
import sys
import time
from pathlib import Path

from label_studio_sdk import Client


def wait_for_labelstudio(url: str, max_retries: int = 30, delay: int = 2) -> bool:
    """Wait for Label Studio to be ready.

    Args:
        url: Label Studio URL
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds

    Returns:
        bool: True if Label Studio is ready, False otherwise
    """
    print(f"Waiting for Label Studio at {url}...")

    for attempt in range(max_retries):
        try:
            import requests
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                print("Label Studio is ready!")
                return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: Label Studio not ready yet...")

        time.sleep(delay)

    print("Label Studio did not become ready in time")
    return False


def create_project(client: Client, project_name: str):
    """Create Label Studio project for PCB defect classification.

    Args:
        client: Label Studio SDK client
        project_name: Name for the project

    Returns:
        Project object or None if project already exists
    """
    # Check if project already exists
    try:
        projects = client.list_projects()
        for project in projects:
            if project.title == project_name:
                print(f"Project '{project_name}' already exists (ID: {project.id})")
                return project
    except Exception as e:
        print(f"Error checking existing projects: {e}")

    # Label config for brush-based segmentation with defect classification
    label_config = """
    <View>
      <Header value="PCB Defect Classification"/>
      <Image name="image" value="$image" zoom="true" zoomControl="true" rotateControl="true"/>

      <BrushLabels name="defects" toName="image">
        <Label value="Solder Bridge" background="#FF0000"/>
        <Label value="Insufficient Solder" background="#FFA500"/>
        <Label value="Cold Joint" background="#FFFF00"/>
        <Label value="Component Damage" background="#00FF00"/>
        <Label value="Missing Component" background="#0000FF"/>
        <Label value="Wrong Component" background="#FF00FF"/>
        <Label value="Misalignment" background="#00FFFF"/>
        <Label value="Contamination" background="#808080"/>
        <Label value="Other Defect" background="#000000"/>
        <Label value="Good" background="#90EE90"/>
      </BrushLabels>

      <Choices name="overall_quality" toName="image" choice="single" required="true">
        <Choice value="Pass"/>
        <Choice value="Fail"/>
        <Choice value="Needs Review"/>
      </Choices>

      <TextArea name="notes" toName="image" placeholder="Additional notes (optional)..." rows="3"/>
    </View>
    """

    try:
        project = client.create_project(
            title=project_name,
            label_config=label_config,
            description="PCB joint image defect classification using brush annotations"
        )

        print(f"Created project: '{project.title}' (ID: {project.id})")
        return project

    except Exception as e:
        print(f"Error creating project: {e}")
        return None


def setup_local_storage(client: Client, project_id: int, storage_path: str):
    """Set up local file storage for the project.

    Args:
        client: Label Studio SDK client
        project_id: Project ID
        storage_path: Path to local storage directory

    Returns:
        Storage object or None if setup fails
    """
    try:
        # Create local file storage
        storage = client.sync_storage.local.create(
            project=project_id,
            path=storage_path,
            use_blob_urls=False,
            regex_filter=".*\\.(jpg|jpeg|png|bmp)$",
            title="PCB Images Storage"
        )

        print(f"Created local storage (ID: {storage['id']})")

        # Sync storage to import existing files
        client.sync_storage.local.sync(storage['id'])
        print("Synced local storage")

        return storage

    except Exception as e:
        print(f"Error setting up local storage: {e}")
        return None


def main():
    """Main initialization function."""
    # Get configuration from environment
    label_studio_url = os.getenv("LABEL_STUDIO_URL", "http://label-studio:8080")
    api_key = os.getenv("LABEL_STUDIO_API_KEY", "")
    project_name = os.getenv("LABEL_STUDIO_PROJECT_NAME", "PCB Defect Classification")
    storage_path = os.getenv("LABEL_STUDIO_STORAGE_PATH", "/labelstudio/data/images")

    print("=" * 60)
    print("Label Studio Project Initialization")
    print("=" * 60)
    print(f"URL: {label_studio_url}")
    print(f"Project Name: {project_name}")
    print(f"Storage Path: {storage_path}")
    print("=" * 60)

    # Wait for Label Studio to be ready
    if not wait_for_labelstudio(label_studio_url):
        print("ERROR: Label Studio is not ready. Exiting.")
        sys.exit(1)

    # Check if API key is provided
    if not api_key:
        print("\nWARNING: No API key provided!")
        print("Please:")
        print("1. Access Label Studio at http://localhost:8080")
        print("2. Create an account or log in")
        print("3. Go to Account & Settings > Access Token")
        print("4. Copy your API key")
        print("5. Set LABEL_STUDIO_API_KEY environment variable")
        print("\nYou can still create the project manually using the Label Studio UI.")
        return

    # Initialize client
    try:
        client = Client(url=label_studio_url, api_key=api_key)
        client.check_connection()
        print("Successfully connected to Label Studio")
    except Exception as e:
        print(f"ERROR: Failed to connect to Label Studio: {e}")
        sys.exit(1)

    # Create project
    project = create_project(client, project_name)
    if not project:
        print("ERROR: Failed to create project")
        sys.exit(1)

    # Set up local storage
    storage = setup_local_storage(client, project.id, storage_path)

    print("\n" + "=" * 60)
    print("Initialization Complete!")
    print("=" * 60)
    print(f"Project ID: {project.id}")
    print(f"Access Label Studio at: {label_studio_url}")
    print("=" * 60)


if __name__ == "__main__":
    main()
