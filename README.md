# ◉ S3 Manager Pro v5.0

> The S3 desktop client that AWS Console should have been.

**75+ features** │ Cross-platform (Windows/Linux/macOS) │ Python + CustomTkinter │ Open Source

Built by [Saurabh Khairkar](https://www.linkedin.com/in/saurabh-khairkar-8398b711b/) — AWS Cloud Engineer

---

## Why This Exists

| Task | AWS Console | aws-cli | S3 Manager Pro |
|------|:-----------:|:-------:|:--------------:|
| Restore 500 Glacier files | Click one by one | Write script | ✅ Select all → Restore (with cost estimate) |
| Resume broken download | Start over | Partial | ✅ Auto-resume from last byte |
| Generate presigned URL | 5 clicks deep | CLI command | ✅ Right-click → Share URL |
| Sync folder with preview | N/A | Blind `aws s3 sync` | ✅ Dry-run table → review → execute |
| Find hidden wasted cost | Check billing | N/A | ✅ Orphaned Upload Cleaner |
| Search across all buckets | Impossible | Complex script | ✅ One search box → results from all buckets |

---

## Install

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/S3_Manager_Pro.git
cd S3_Manager_Pro

# Install dependencies
pip install boto3 customtkinter keyring plyer

# Run
python -m s3_manager_pro_v5
```

### Requirements
- Python 3.10+
- AWS credentials (Access Key or AWS Profile)

### Platform Support
| OS | Status |
|----|--------|
| Windows 10/11 | ✅ Fully tested |
| Ubuntu/Debian Linux | ✅ Works (`sudo apt install python3-tk` first) |
| macOS | ✅ Works |

---

## Features (75+)

### Core Operations
- ⬇ **Parallel Download** with auto-resume
- ⬆ **Upload** (files/folders, any size up to 5 TB)
- 📤 **Copy/Move** between buckets (multipart for large files)
- 🗑 **Delete** with confirmation
- ✏️ **Batch Rename** (prefix, suffix, find-replace)
- 🔗 **Presigned URL** generator (1 hour to 7 days)
- 📋 **S3 Sync** with dry-run preview
- ⏰ **Scheduled Auto-Sync** (like Dropbox)

### Smart Features (Unique — No Other Tool Has These)
- 💡 **Cost Advisor** — "Move 200 files to Glacier = save $45/month" with one-click apply
- 💰 **Cost Intelligence Center** — access patterns, trends, budget alerts, region comparison
- 🧹 **Orphaned Multipart Cleaner** — finds invisible wasted storage costing you money
- 🛡️ **Security Health Check** — scans all buckets for public access, encryption, versioning issues
- 🔍 **Smart Search** — search filenames across ALL buckets at once
- 📊 **Bucket Analytics** — visual storage breakdown, file types, top largest files
- 🧊 **Smart Glacier Restore** — shows $/tier comparison before restoring
- 📈 **Real-time Speed Graph** — live transfer speed chart

### File Management
- 👁 **File Preview** — view text/JSON/CSV/images inline without downloading
- 🌐 **Open in Browser** — video/audio/PDF open via presigned URL in browser
- 📜 **File Versioning** — view all versions, restore old versions
- 🔀 **Diff Viewer** — compare two file versions side-by-side
- 🏷️ **Bulk Tag Editor** — add/remove tags on hundreds of files at once
- 🔄 **Storage Class Change** — bulk change with cost comparison
- 📁 **Folder Size Calculator** — instant size for current view

### Bucket Management
- 🪣 **Create/Delete Buckets** — with encryption, versioning, public block
- 🔐 **ACL & Permissions Editor** — bucket policy JSON editor
- 🌐 **CORS Configuration** — view/edit with presets
- 🌍 **Static Website Hosting** — enable/disable, set index/error docs
- 🔒 **Object Lock/Retention** — view governance/compliance settings

### Infrastructure & DevOps
- ☁️ **CloudFront Invalidation** — invalidate CDN cache after upload
- 🚦 **Bandwidth Throttle** — limit speed (1-100 MB/s)
- 👤 **Multi-Account Profiles** — switch between AWS accounts
- 📋 **Export to CSV** — export file listings for auditing

### User Experience
- 🌙 **Dark/Light Theme** — toggle with one click
- 🎓 **Guided Tour** — 10-step interactive walkthrough
- 📖 **Feature Guide** — every feature explained in simple words
- 💬 **Tooltips** — hover any button to see what it does
- ✅ **Toast Notifications** — green banner on success
- ☐☑ **Clear Checkboxes** — obvious selection state
- ⌨️ **20+ Keyboard Shortcuts** — power user productivity

---

## Screenshots

> *Add screenshots here after taking them*

---

## Architecture

```
s3_manager_pro_v5/
├── app.py                    # Main controller
├── backend/
│   ├── auth.py              # Secure credentials (OS keyring)
│   ├── s3_client.py         # S3 API operations
│   ├── transfer.py          # Parallel download/upload engine
│   ├── pricing.py           # Cost estimation (AWS Cost Explorer + local)
│   └── large_file_ops.py    # Multipart copy/move (any size up to 5 TB)
├── ui/
│   ├── menu_bar.py          # File/Edit/View/Bucket/Tools/Help
│   ├── toolbar.py           # Icon toolbar with text labels
│   ├── sidebar.py           # Bucket tree + stats + bookmarks
│   ├── file_table.py        # Paginated sortable table
│   ├── details_panel.py     # Right panel (file info + actions)
│   ├── wizard.py            # First-launch setup wizard
│   ├── guided_tour.py       # Interactive walkthrough
│   ├── help_guide.py        # Feature guide database
│   ├── toast.py             # Success notification banners
│   ├── tooltip.py           # Hover tooltips
│   └── dialogs/             # 30+ feature dialogs
└── utils/
    ├── constants.py          # Themes, config
    └── formatting.py         # Size/duration/icon helpers
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+D` | Download selected |
| `Ctrl+U` | Upload files |
| `Ctrl+A` | Select all |
| `Ctrl+F` | Filter/Search |
| `Ctrl+Shift+F` | Smart Search (all buckets) |
| `Ctrl+P` | Preview file |
| `Ctrl+L` | Generate share URL |
| `Ctrl+E` | Export to CSV |
| `Ctrl+I` | Properties |
| `Ctrl+T` | Transfer queue |
| `F5` | Refresh |
| `Delete` | Delete selected |
| `Backspace` | Go up one folder |
| `Space` | Toggle selection |
| `Enter` | Open folder / Download |

---

## Built With

- **Python 3.13** — Core language
- **CustomTkinter** — Modern GUI framework
- **boto3** — AWS SDK
- **keyring** — Secure credential storage
- **plyer** — System notifications
- **Pillow** — Image preview + icon generation

---

## Author

**Saurabh Khairkar**
- AWS Cloud Engineer
- LinkedIn: [saurabh-khairkar](https://www.linkedin.com/in/saurabh-khairkar-8398b711b/)

Built with AI-assisted development.

---

## License

MIT License — free to use, modify, and distribute.
