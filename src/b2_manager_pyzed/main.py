import pyzed as pz
import os
import sys
import subprocess
import threading
from b2sdk.v2 import InMemoryAccountInfo, B2Api


class B2Manager(pz.App):
    title = "B2 Cloud Storage Manager"
    size = (1200, 800)
    theme = "One Dark"  # Modern dark theme

    def __init__(self):
        super().__init__()
        self.b2_api = None
        self.account_info = InMemoryAccountInfo()
        self.selected_bucket = None
        self.selected_file = None
        self.current_folder = ""
        self.file_dict = {}
        self.buckets = []
        self.files = []
        self.key_id = ""
        self.key = ""
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.upload_path = ""
        self.status = "Ready"
        self.progress = 0
        self.connected = False

    def view(self):
        # Main container with gradient background effect
        return pz.container(
            pz.column(
                # Header with gradient effect
                pz.container(
                    pz.row(
                        pz.text("☁️", size=40),
                        pz.column(
                            pz.text("B2 Cloud Storage", size=28, weight="bold"),
                            pz.text("Manager", size=16, color="#888"),
                        ),
                        spacing=10,
                    ),
                    padding=30,
                    background="#1a1a2e",
                ),
                # Authentication Section
                pz.container(
                    pz.column(
                        pz.text("🔐 Authentication", size=18, weight="bold", color="#4ade80"),
                        pz.row(
                            pz.column(
                                pz.text("Application Key ID:", size=12, color="#888"),
                                pz.input(
                                    placeholder="Enter Key ID",
                                    value=self.key_id,
                                    on_change=lambda text: setattr(self, "key_id", text),
                                ),
                            ),
                            pz.column(
                                pz.text("Application Key:", size=12, color="#888"),
                                pz.input(
                                    placeholder="Enter Key",
                                    value=self.key,
                                    password=True,
                                    on_change=lambda text: setattr(self, "key", text),
                                ),
                            ),
                            pz.button(
                                "Connect",
                                self.connect,
                                background="#4ade80",
                                color="#000",
                                weight="bold",
                            ),
                            spacing=20,
                        ),
                    ),
                    padding=20,
                    background="#16213e",
                    border_radius=12,
                ),
                # Main content area
                pz.row(
                    # Buckets panel
                    pz.container(
                        pz.column(
                            pz.text("📦 Buckets", size=16, weight="bold", color="#60a5fa"),
                            pz.list(
                                self.buckets,
                                on_select=self.on_bucket_select,
                                min_height=400,
                            ),
                        ),
                        padding=20,
                        background="#0f3460",
                        border_radius=12,
                        min_width=300,
                    ),
                    # Files panel
                    pz.container(
                        pz.column(
                            pz.row(
                                pz.text("📁 Files", size=16, weight="bold", color="#60a5fa"),
                                pz.button("↑ Back", self.go_back, enabled=self.current_folder != ""),
                                spacing=10,
                            ),
                            pz.text(self.current_folder or "Root", size=12, color="#888"),
                            pz.list(
                                self.files,
                                on_select=self.on_file_select,
                                on_double_click=self.on_file_double_click,
                                min_height=350,
                            ),
                        ),
                        padding=20,
                        background="#0f3460",
                        border_radius=12,
                        fill=True,
                    ),
                    spacing=20,
                    fill=True,
                ),
                # Upload/Download panel
                pz.container(
                    pz.row(
                        pz.column(
                            pz.text("📤 Upload", size=14, weight="bold", color="#f472b6"),
                            pz.row(
                                pz.input(
                                    placeholder="Select file to upload",
                                    value=self.upload_path,
                                    on_change=lambda text: setattr(self, "upload_path", text),
                                ),
                                pz.button("Browse", self.browse_upload),
                                pz.button("Upload", self.upload_file, background="#f472b6"),
                                spacing=10,
                            ),
                        ),
                        pz.column(
                            pz.text("📥 Download", size=14, weight="bold", color="#f472b6"),
                            pz.row(
                                pz.input(
                                    placeholder="Download path",
                                    value=self.download_path,
                                    on_change=lambda text: setattr(self, "download_path", text),
                                ),
                                pz.button("Browse", self.browse_download),
                                pz.button("Download", self.download_file, background="#f472b6"),
                                pz.button("Delete", self.delete_file, background="#ef4444"),
                                spacing=10,
                            ),
                        ),
                        spacing=30,
                    ),
                    padding=20,
                    background="#16213e",
                    border_radius=12,
                ),
                # Status bar
                pz.container(
                    pz.row(
                        pz.text(f"Status: {self.status}", size=12, color="#888"),
                        pz.progress(value=self.progress, min_height=8),
                    ),
                    padding=15,
                    background="#1a1a2e",
                ),
                spacing=20,
                padding=30,
            ),
            background="#0d1117",
        )

    def connect(self):
        if not self.key_id or not self.key:
            self.status = "Please enter credentials"
            return

        self.status = "Connecting..."
        self.progress = 10

        def connect_thread():
            try:
                self.b2_api = B2Api(self.account_info)
                self.b2_api.authorize_account("production", self.key_id, self.key)
                self.connected = True
                self.list_buckets()
                self.status = "Connected successfully!"
                self.progress = 100
            except Exception as e:
                self.status = f"Connection failed: {str(e)}"
                self.progress = 0
                self.connected = False

        threading.Thread(target=connect_thread, daemon=True).start()

    def list_buckets(self):
        if not self.b2_api:
            return
        try:
            buckets = self.b2_api.list_buckets()
            self.buckets = [bucket.name for bucket in buckets]
        except Exception as e:
            self.status = f"Error listing buckets: {str(e)}"

    def on_bucket_select(self, index):
        if index >= 0 and index < len(self.buckets):
            self.selected_bucket = self.buckets[index]
            self.current_folder = ""
            self.list_files()

    def list_files(self):
        if not self.selected_bucket or not self.b2_api:
            return

        try:
            bucket = self.b2_api.get_bucket_by_name(self.selected_bucket)
            self.files = []
            self.file_dict = {}

            for file_version, folder_name in bucket.ls(folder_to_list=self.current_folder, latest_only=True):
                if folder_name:
                    display_name = folder_name[len(self.current_folder):] if self.current_folder else folder_name
                    if display_name.endswith("/"):
                        display_name = display_name[:-1]
                    self.files.append(f"📁 {display_name}")
                else:
                    file_name = file_version.file_name[len(self.current_folder):] if self.current_folder else file_version.file_name
                    size = self.format_size(file_version.size)
                    display_item = f"📄 {file_name} ({size})"
                    self.files.append(display_item)
                    self.file_dict[display_item] = (file_version.id_, file_version.file_name)

        except Exception as e:
            self.status = f"Error listing files: {str(e)}"

    def format_size(self, size):
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def on_file_select(self, index):
        if index >= 0 and index < len(self.files):
            self.selected_file = self.files[index]

    def on_file_double_click(self, index):
        if index >= 0 and index < len(self.files):
            item = self.files[index]
            if item.startswith("📁"):
                folder_name = item[2:].strip()
                if self.current_folder:
                    self.current_folder = self.current_folder + "/" + folder_name
                else:
                    self.current_folder = folder_name
                self.list_files()

    def go_back(self):
        if self.current_folder:
            parent = os.path.dirname(self.current_folder)
            self.current_folder = parent
            self.list_files()

    def browse_upload(self):
        # TODO: Implement file dialog
        self.status = "Select a file to upload"

    def browse_download(self):
        # TODO: Implement folder dialog
        self.status = "Select download folder"

    def upload_file(self):
        if not self.selected_bucket or not self.b2_api:
            self.status = "Please connect and select a bucket first"
            return

        if not self.upload_path or not os.path.exists(self.upload_path):
            self.status = "Please select a valid file"
            return

        filename = os.path.basename(self.upload_path)
        b2_filename = self.current_folder + "/" + filename if self.current_folder else filename

        self.status = "Uploading..."
        self.progress = 0

        def upload_thread():
            try:
                bucket = self.b2_api.get_bucket_by_name(self.selected_bucket)
                bucket.upload_local_file(local_file=self.upload_path, file_name=b2_filename)
                self.status = "Upload successful!"
                self.progress = 100
                self.list_files()
            except Exception as e:
                self.status = f"Upload failed: {str(e)}"
                self.progress = 0

        threading.Thread(target=upload_thread, daemon=True).start()

    def download_file(self):
        if not self.selected_file or not self.selected_bucket or not self.b2_api:
            self.status = "Please select a file first"
            return

        if self.selected_file.startswith("📁"):
            self.status = "Cannot download folders"
            return

        if self.selected_file not in self.file_dict:
            self.status = "File information not found"
            return

        file_id, b2_filename = self.file_dict[self.selected_file]
        output_path = os.path.join(self.download_path, os.path.basename(b2_filename))

        self.status = "Downloading..."
        self.progress = 0

        def download_thread():
            try:
                # Use b2-windows.exe CLI for download
                if getattr(sys, "frozen", False):
                    # Running as EXE - b2-windows.exe should be in the same directory
                    b2_cli_path = os.path.join(os.path.dirname(sys.executable), "b2-windows.exe")
                else:
                    # Running as script
                    b2_cli_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "b2-windows.exe")

                if not os.path.exists(b2_cli_path):
                    b2_cli_path = r"C:\Users\USER\Downloads\b2-windows.exe"

                cmd = [b2_cli_path, "file", "download", f"b2id://{file_id}", output_path]

                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE

                result = subprocess.run(
                    cmd,
                    startupinfo=startupinfo,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

                if result.returncode != 0:
                    raise Exception(f"CLI download failed: {result.stderr}")

                self.status = "Download successful!"
                self.progress = 100
            except Exception as e:
                self.status = f"Download failed: {str(e)}"
                self.progress = 0

        threading.Thread(target=download_thread, daemon=True).start()

    def delete_file(self):
        if not self.selected_file or not self.selected_bucket or not self.b2_api:
            self.status = "Please select a file first"
            return

        if self.selected_file.startswith("📁"):
            self.status = "Cannot delete folders"
            return

        if self.selected_file not in self.file_dict:
            self.status = "File information not found"
            return

        file_id, b2_filename = self.file_dict[self.selected_file]

        self.status = "Deleting..."
        self.progress = 0

        def delete_thread():
            try:
                bucket = self.b2_api.get_bucket_by_name(self.selected_bucket)
                bucket.delete_file_version(file_id, b2_filename)
                self.status = "Delete successful!"
                self.progress = 100
                self.list_files()
            except Exception as e:
                self.status = f"Delete failed: {str(e)}"
                self.progress = 0

        threading.Thread(target=delete_thread, daemon=True).start()


if __name__ == "__main__":
    pz.run(B2Manager)
