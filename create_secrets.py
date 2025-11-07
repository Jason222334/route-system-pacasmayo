import os

def main():
    secrets_path = "/opt/render/project/src/.streamlit/secrets.toml"
    os.makedirs(os.path.dirname(secrets_path), exist_ok=True)

    content = f"""
SUPABASE_URL = "{os.getenv('SUPABASE_URL')}"
SUPABASE_KEY = "{os.getenv('SUPABASE_KEY')}"
GOOGLE_MAPS_API_KEY = "{os.getenv('GOOGLE_MAPS_API_KEY')}"
N8N_WEBHOOK_URL = "{os.getenv('N8N_WEBHOOK_URL')}"
"""

    with open(secrets_path, "w") as f:
        f.write(content.strip())

    print("✅ secrets.toml creado correctamente en Render")

if __name__ == "__main__":
    main()
