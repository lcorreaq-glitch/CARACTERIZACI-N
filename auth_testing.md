# Auth Testing Checklist Used for Bug Verification

Focused auth checks for the reported login/password reset bug:

1. Verify the persisted user record exists, is active, has `must_change_password=false`, and the bcrypt hash accepts the expected new password but rejects the old password.
2. Verify `POST /api/auth/login` returns 200 with an access token and expected user payload for the new password.
3. Verify `POST /api/auth/login` returns 401 for the old password.
4. Verify authenticated `/api/auth/me` succeeds with the returned bearer token.
5. Verify the React `/login` UI accepts the new password and redirects to `/`, not `/change-password`.
