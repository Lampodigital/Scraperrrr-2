import modal
import os

app = modal.App("cookie-sync")
vol = modal.Volume.from_name("glaido-data")

@app.function(volumes={"/data": vol})
def sync_cookies():
    local_files = [
        ".tmp/cookies_bensbites.json",
        ".tmp/cookies_rundown.json"
    ]
    
    for filename in local_files:
        if os.path.exists(filename):
            print(f"Reading {filename}...")
            with open(filename, "r") as f:
                content = f.read()
                remote_path = os.path.basename(filename)
                with open(f"/data/{remote_path}", "w") as remote_file:
                    remote_file.write(content)
            print(f"✅ Synced {filename}")
        else:
            print(f"⚠️ {filename} not found locally.")
    
    vol.commit()

if __name__ == "__main__":
    with app.run():
        sync_cookies.remote()
