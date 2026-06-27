import os
import json

# Token window management: files we allow the agent to read
CORE_EXTENSIONS = {'.py', '.js', '.ts', '.jsx', '.tsx', '.c', '.cpp', '.h', '.css', '.html', '.md', '.java', '.go'}

def get_repo_tree(repo_path: str) -> str:
    """Returns the file directory structure of the repository."""
    if not os.path.exists(repo_path):
        return f"Error: Repository path '{repo_path}' does not exist."
    
    tree = []
    for root, dirs, files in os.walk(repo_path):
        # Ignore common massive directories
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'venv', '__pycache__', 'dist', 'build')]
        level = root.replace(repo_path, '').count(os.sep)
        indent = ' ' * 4 * (level)
        tree.append(f"{indent}{os.path.basename(root)}/")
        subindent = ' ' * 4 * (level + 1)
        for f in files:
            tree.append(f"{subindent}{f}")
    return "\n".join(tree)

def read_code_file(repo_path: str, file_path: str) -> str:
    """Fetches raw text contents of a specific file."""
    # Ensure file_path is relative to repo_path
    if file_path.startswith('/'):
        file_path = file_path[1:]
        
    full_path = os.path.join(repo_path, file_path)
    
    # Prevent directory traversal
    if not os.path.abspath(full_path).startswith(os.path.abspath(repo_path)):
         return f"Error: Path traversal detected. Cannot read '{file_path}'."
         
    if not os.path.exists(full_path):
        return f"Error: File '{file_path}' does not exist."
    
    # Token Window Management: Check file extension
    _, ext = os.path.splitext(full_path)
    if ext not in CORE_EXTENSIONS and ext != '':
        return f"Error: Cannot read '{file_path}'. Extension '{ext}' is not considered a core logic file. To save context tokens, focus on core logic files."
    
    # Token Window Management: Check file size (e.g., max 50KB to prevent context overflow)
    if os.path.getsize(full_path) > 50000:
        return f"Error: File '{file_path}' is too large. Reading aborted to protect token window."

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def update_portfolio_db(project_id: str, clean_json_payload: dict) -> str:
    """Permanently writes verified project metadata to the frontend database."""
    # Data Integrity Guardrails
    db_path = "portfolio_db.json"
    
    db_data = {}
    if os.path.exists(db_path):
        with open(db_path, 'r') as f:
            db_data = json.load(f)
            
    # Verification check: Ensure we don't blindly overwrite existing projects without logging
    if project_id in db_data:
        print(f"[Guardrail Alert] Project {project_id} already exists. Proceeding with verified overwrite...")
    else:
        print(f"[Guardrail] Creating new project entry: {project_id}")
        
    db_data[project_id] = clean_json_payload
    
    # Safely write to database
    try:
        with open(db_path, 'w') as f:
            json.dump(db_data, f, indent=2)
        return f"Success: Portfolio database updated securely for project {project_id}."
    except Exception as e:
        return f"Database Error: Failed to write to {db_path} - {str(e)}"
