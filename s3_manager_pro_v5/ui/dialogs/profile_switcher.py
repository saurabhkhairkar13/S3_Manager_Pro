"""Multi-Account Profile Switcher — save and switch between AWS accounts."""
import json
import os
import logging
import customtkinter as ctk
from s3_manager_pro_v5.utils.constants import DARK_THEME, LIGHT_THEME

logger = logging.getLogger(__name__)

PROFILES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "s3_profiles.json"
)


class ProfileManager:
    """Manages multiple AWS account profiles."""

    def __init__(self):
        self._profiles = self._load()

    def _load(self) -> list:
        if not os.path.exists(PROFILES_FILE):
            return []
        try:
            with open(PROFILES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def _save(self):
        try:
            with open(PROFILES_FILE, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def add_profile(self, name: str, auth_mode: str, region: str,
                    profile_name: str = "", account_id: str = ""):
        """Add a new account profile (credentials stored separately via keyring)."""
        entry = {
            "name": name,
            "auth_mode": auth_mode,
            "aws_profile": profile_name,
            "region": region,
            "account_id": account_id,
        }
        # Replace if same name exists
        self._profiles = [p for p in self._profiles if p["name"] != name]
        self._profiles.append(entry)
        self._save()

    def remove_profile(self, name: str):
        self._profiles = [p for p in self._profiles if p["name"] != name]
        self._save()

    def get_profile(self, name: str) -> dict:
        for p in self._profiles:
            if p["name"] == name:
                return p
        return {}

    @property
    def profiles(self) -> list:
        return self._profiles

    @property
    def profile_names(self) -> list:
        return [p["name"] for p in self._profiles]


class ProfileSwitcherDialog:
    """Dialog to manage and switch between AWS account profiles."""

    def __init__(self, parent, app):
        self.app = app
        self.profile_mgr = ProfileManager()

        colors = DARK_THEME if app.is_dark else LIGHT_THEME

        self.win = ctk.CTkToplevel(parent)
        self.win.title("👤 Account Profiles")
        self.win.geometry("450x460")
        self.win.transient(parent)
        self.win.grab_set()
        self.win.resizable(False, True)
        self.win.configure(fg_color=colors["bg"])

        # Title
        ctk.CTkLabel(self.win, text="👤 Account Profiles",
                     font=ctk.CTkFont(size=16, weight="bold"),
                     text_color=colors["text_primary"]).pack(pady=(20, 10))

        ctk.CTkLabel(self.win, text="Switch between saved AWS accounts",
                     font=ctk.CTkFont(size=12),
                     text_color=colors["text_secondary"]).pack(pady=(0, 15))

        # Profile list
        self.list_frame = ctk.CTkScrollableFrame(self.win, fg_color="transparent", height=200)
        self.list_frame.pack(fill="both", expand=True, padx=20)

        self._populate_profiles()

        # Buttons
        btn_frame = ctk.CTkFrame(self.win, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))

        ctk.CTkButton(btn_frame, text="+ Add Current Account", width=170, height=34,
                      corner_radius=8, fg_color=colors["primary"],
                      hover_color=colors["primary_hover"],
                      font=ctk.CTkFont(size=12, weight="bold"),
                      command=self._save_current).pack(side="left", padx=(0, 10))

        ctk.CTkButton(btn_frame, text="Close", width=70, height=34,
                      corner_radius=8, fg_color=colors["badge_bg"],
                      hover_color=colors["surface_hover"],
                      text_color=colors["text_primary"],
                      command=self.win.destroy).pack(side="right")

    def _populate_profiles(self):
        """Render saved profiles."""
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        colors = DARK_THEME if self.app.is_dark else LIGHT_THEME

        if not self.profile_mgr.profiles:
            ctk.CTkLabel(self.list_frame, text="No saved profiles.\nClick 'Add Current Account' to save.",
                         font=ctk.CTkFont(size=12),
                         text_color=colors["text_secondary"]).pack(pady=20)
            return

        for profile in self.profile_mgr.profiles:
            card = ctk.CTkFrame(self.list_frame, fg_color=colors["surface"], corner_radius=8)
            card.pack(fill="x", pady=3)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)

            # Name + account
            ctk.CTkLabel(inner, text=f"👤 {profile['name']}",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=colors["text_primary"]).pack(anchor="w")

            detail = f"{profile.get('region', '')} │ {profile.get('account_id', 'N/A')}"
            ctk.CTkLabel(inner, text=detail,
                         font=ctk.CTkFont(size=10),
                         text_color=colors["text_secondary"]).pack(anchor="w")

            # Buttons
            btn_row = ctk.CTkFrame(inner, fg_color="transparent")
            btn_row.pack(anchor="e")

            ctk.CTkButton(btn_row, text="Switch", width=65, height=26,
                          corner_radius=4, font=ctk.CTkFont(size=10),
                          fg_color=colors["success"], hover_color="#1fa339",
                          command=lambda p=profile: self._switch_to(p)).pack(side="left", padx=2)

            ctk.CTkButton(btn_row, text="✕", width=26, height=26,
                          corner_radius=4, font=ctk.CTkFont(size=10),
                          fg_color=colors["danger"], hover_color=colors["danger_hover"],
                          command=lambda p=profile: self._remove_profile(p)).pack(side="left", padx=2)

    def _save_current(self):
        """Save the currently connected account as a profile."""
        if not self.app.s3_client or not self.app.s3_client.is_connected:
            from tkinter import messagebox
            messagebox.showwarning("Not Connected", "Connect to an account first.", parent=self.win)
            return

        name = f"{self.app.s3_client.user_name}@{self.app.s3_client.account_id}"
        self.profile_mgr.add_profile(
            name=name,
            auth_mode=self.app.cred_manager.get("auth_mode", "keys"),
            region=self.app.cred_manager.get("region", "ap-south-1"),
            profile_name=self.app.cred_manager.get("profile", ""),
            account_id=self.app.s3_client.account_id,
        )
        self._populate_profiles()

    def _switch_to(self, profile: dict):
        """Switch to a different account profile."""
        # Update settings
        settings = self.app.cred_manager.settings.copy()
        settings["auth_mode"] = profile["auth_mode"]
        settings["region"] = profile["region"]
        settings["profile"] = profile.get("aws_profile", "")
        self.app.cred_manager.save_settings(settings)

        # Reconnect
        self.win.destroy()
        self.app._auto_connect()

    def _remove_profile(self, profile: dict):
        """Remove a saved profile."""
        from tkinter import messagebox
        if messagebox.askyesno("Remove Profile",
                               f"Remove profile '{profile['name']}'?", parent=self.win):
            self.profile_mgr.remove_profile(profile["name"])
            self._populate_profiles()
