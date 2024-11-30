import streamlit as st
from typing import List
import os
from dotenv import load_dotenv

load_dotenv()

class AuthManager:
    """Handles user authentication and authorization for the application."""
    
    def __init__(self):
        self.allowed_emails = self._load_allowed_emails()

    def _load_allowed_emails(self) -> List[str]:
        """Load allowed emails from environment variable."""
        emails_str = os.getenv('ALLOWED_EMAILS', '')
        return [email.strip() for email in emails_str.split(',') if email.strip()]

    def check_authentication(self) -> bool:
        """
        Verify if user is authenticated and authorized.
        Returns True if user is authenticated and authorized, False otherwise.
        """
        # Initialize session state
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False

        if not st.session_state.authenticated:
            self._show_login_form()
            return False
        return True

    def _show_login_form(self):
        """Display login form and handle authentication."""
        st.title("Login")
        
        # Simple email input form
        email = st.text_input("Email")
        if st.button("Login"):
            if email in self.allowed_emails:
                st.session_state.authenticated = True
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("Unauthorized email address")

    def logout(self):
        """Clear authentication state."""
        st.session_state.authenticated = False
        st.session_state.user_email = None