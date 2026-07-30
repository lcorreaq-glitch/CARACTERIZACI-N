"""Reference Playwright flow used via browser automation tool for the superadmin login bug.

Steps:
1. Navigate to /login.
2. Clear localStorage.
3. Fill data-testid login-email-input with lcorreaq@gmail.com.
4. Fill data-testid login-password-input with IUDigital2026.
5. Click data-testid login-submit-button.
6. Assert final route is / and not /change-password, with token/user stored in localStorage.
"""
