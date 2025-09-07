import requests
import time
import json

# Base URL of the Flask API
BASE_URL = "http://127.0.0.1:5000"


def test_upload_audio(file_path):
    """Test the /upload_audio endpoint by uploading an audio file."""
    url = f"{BASE_URL}/upload_audio"
    files = {"file": open(file_path, "rb")}

    print(f"Uploading {file_path}...")
    response = requests.post(url, files=files)

    if response.status_code == 200:
        print("✅ Upload successful!")
        result = response.json()
        print(result)
        return result.get("task_id")
    else:
        print("❌ Upload failed!")
        print(response.text)
        return None


def test_task_status(task_id):
    """Test the /task_status/<task_id> endpoint to check processing status."""
    url = f"{BASE_URL}/task_status/{task_id}"
    print(f"Checking status for task: {task_id}...")

    while True:
        response = requests.get(url)
        if response.status_code == 200:
            result = response.json()
            print(result)
            if result["status"] == "completed" or result["status"] == "failed":
                if result["status"] == "completed":
                    # Print detailed results
                    print("\n=== DETAILED RESULTS ===")
                    print(f"Fluency Score: {result['result'].get('fluency_score')}")
                    print(f"Severity: {result['result'].get('severity')}")
                    print(f"Repetitions: {result['result'].get('num_repetitions')}")
                    print(f"Fillers: {result['result'].get('num_fillers')}")
                    print(
                        f"Prolongations: {result['result'].get('num_prolongations', 0)}"
                    )
                    print(f"Blocks: {result['result'].get('num_blocks', 0)}")

                    # Test passage comparison endpoint
                    test_passage_comparison(task_id)

                    # Print stutter events
                    print_stutter_events(result["result"].get("stutter_events", []))
                break
        else:
            print("❌ Failed to check status!")
            print(response.text)
            break

        print("⏳ Still processing... Checking again in 10 seconds.")
        time.sleep(10)


def print_stutter_events(events):
    """Print stutter events in a readable format."""
    if not events:
        print("\nNo stutter events detected.")
        return

    print("\n=== STUTTER EVENTS ===")

    # Group events by type
    event_types = {}
    for event in events:
        event_type = event.get("type", "unknown")
        if event_type not in event_types:
            event_types[event_type] = []
        event_types[event_type].append(event)

    # Print each type
    for event_type, type_events in event_types.items():
        print(f"\n{event_type.upper()} ({len(type_events)}):")
        for i, event in enumerate(type_events[:5], 1):  # Show first 5 of each type
            start = event.get("start", 0)
            duration = event.get("duration", 0)
            text = event.get("text", "")
            subtype = event.get("subtype", "")

            print(
                f"  {i}. {text} ({subtype}) at {start:.2f}s, duration: {duration:.2f}s"
            )

        if len(type_events) > 5:
            print(f"  ... and {len(type_events) - 5} more {event_type} events")


def test_passage_comparison(task_id):
    """Test the /get_passage_comparison/<task_id> endpoint."""
    url = f"{BASE_URL}/get_passage_comparison/{task_id}"
    print(f"\nChecking passage comparison for task: {task_id}...")

    response = requests.get(url)
    if response.status_code == 200:
        result = response.json()
        print("✅ Passage comparison retrieved!")
        print(f"Filtered Discrepancies: {result.get('discrepancy_count', 0)}")
        print(f"Raw Discrepancies: {result.get('raw_discrepancy_count', 0)}")

        # Print some example discrepancies
        discrepancies = result.get("discrepancies", [])
        if discrepancies:
            print("\nExample discrepancies:")
            for i, disc in enumerate(discrepancies[:5]):  # Show first 5
                print(f"{i+1}. Type: {disc.get('type')}")
                if "transcribed" in disc:
                    print(f"   Transcribed: {disc.get('transcribed')}")
                if "reference" in disc:
                    print(f"   Reference: {disc.get('reference')}")
                if "words" in disc:
                    print(f"   Words: {', '.join(disc.get('words'))}")
                if "count" in disc and disc.get("type") == "repetition":
                    print(f"   Repeated {disc.get('count')} times")
    else:
        print("❌ Failed to retrieve passage comparison!")
        print(response.text)


def test_api():
    """Runs the full test sequence for the API."""
    TEST_AUDIO_FILE = "test.mp4"

    # Step 1: Upload Audio
    task_id = test_upload_audio(TEST_AUDIO_FILE)
    if task_id:
        # Step 2: Check Task Status
        test_task_status(task_id)


if __name__ == "__main__":
    test_api()
