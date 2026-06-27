import os
import argparse
from agent import analyze_repository

def setup_dummy_repo(path: str):
    """Creates a dummy repository for testing the agent's constraints."""
    os.makedirs(os.path.join(path, "src"), exist_ok=True)
    os.makedirs(os.path.join(path, "node_modules", "massive-lib"), exist_ok=True)
    
    # Core logic file that the agent SHOULD read
    with open(os.path.join(path, "src", "index.js"), "w") as f:
        f.write('''
// High performance custom state manager
class CustomStore {
    constructor() {
        this.state = {};
        this.listeners = [];
    }
    // ... complex logic ...
}

// Uses native Web Speech API for voice commands without external wrappers
const recognition = new webkitSpeechRecognition();
recognition.continuous = true;
recognition.lang = "en-US";
''')
    
    # Non-core file that the agent SHOULD BE BLOCKED from reading
    with open(os.path.join(path, "package-lock.json"), "w") as f:
        f.write('{"name": "dummy", "lockfileVersion": 2, "dependencies": {"massive-lib": {"version": "1.0.0"}}}')
    
    # Massive file that should trigger token size limits
    with open(os.path.join(path, "src", "large-data.json"), "w") as f:
        f.write('{"data": "' + 'a' * 60000 + '"}')
    
    # Dummy readme
    with open(os.path.join(path, "README.md"), "w") as f:
        f.write('# Voice UI App\\n\\nProvides a high-performance voice-driven user interface aiming for sub-200ms latency.')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AntiGravity Core Portfolio Analyzer")
    parser.add_argument("--repo", type=str, default="./dummy_repo", help="Path to repository to analyze")
    parser.add_argument("--project-id", type=str, default="proj-001", help="Project ID for DB")
    parser.add_argument("--setup-dummy", action="store_true", help="Setup dummy repository for testing before running")
    
    args = parser.parse_args()
    
    if args.setup_dummy:
        print(f"Setting up dummy repo at {args.repo}...")
        setup_dummy_repo(args.repo)
        
    import json
    
    # Run Analysis
    result = analyze_repository(args.repo, args.project_id)
    
    if result:
        try:
            with open("portfolio_data.json", "w", encoding="utf-8") as f:
                json.dump(result.model_dump(), f, indent=2)
            print("Successfully saved structured payload to portfolio_data.json")
        except Exception as e:
            print(f"Error saving portfolio data to file: {e}")
