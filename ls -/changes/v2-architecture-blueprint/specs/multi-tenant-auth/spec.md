## ADDED Requirements

### Requirement: User Registration & Login
User accounts with email/password authentication using JWT tokens.

#### Scenario: New user registration
- **WHEN** a POST request is made to `/auth/register` with `username`, `email`, and `password`
- **THEN** a new `users` row is created with `password_hash` (bcrypt), `account_type=PAPER`, `cash_balance=100000`, and a 201 response returns a JWT access token (15min) + refresh token (7d)

#### Scenario: User login
- **WHEN** a POST request is made to `/auth/login` with valid `email` and `password`
- **THEN** a JWT access token (15min) and refresh token (7d) are returned in `httpOnly` cookies with `Secure` and `SameSite=Strict` flags

#### Scenario: Token refresh
- **WHEN** the access token expires and a valid refresh token is presented to `/auth/refresh`
- **THEN** a new access token is issued and the refresh token is rotated (old one invalidated)

#### Scenario: Invalid credentials
- **WHEN** login is attempted with wrong email or password
- **THEN** a 401 response is returned with generic message "Invalid credentials" (no email enumeration)

---

### Requirement: Tenant Isolation
All business data is scoped to the authenticated user via `user_id`.

#### Scenario: API request without JWT
- **WHEN** any API endpoint (except `/auth/*`, `/healthz`, `/readyz`) is called without a valid JWT
- **THEN** a 401 Unauthorized response is returned

#### Scenario: Cross-tenant data access
- **WHEN** user A attempts to access user B's orders, positions, or watchlist via API
- **THEN** a 404 Not Found is returned (not 403, to avoid confirming existence)

#### Scenario: All queries scoped
- **WHEN** any database query is executed in the context of an authenticated request
- **THEN** it MUST include `WHERE user_id = :current_user_id` (enforced by service layer dependency injection)

---

### Requirement: Broker Credential Encryption
API secrets are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256).

#### Scenario: Storing broker credentials
- **WHEN** a user submits broker API key and secret via `/settings/broker`
- **THEN** `api_key` is stored as plaintext, `api_secret_encrypted` is encrypted with Fernet before DB write, and `webhook_tokens_encrypted` JSONB values are individually encrypted

#### Scenario: Reading broker credentials
- **WHEN** the execution engine needs broker credentials for order submission
- **THEN** `api_secret_encrypted` is decrypted in-memory, used for the API call, and never logged or cached

#### Scenario: Fernet key unavailable
- **WHEN** the `FERNET_KEY` environment variable is missing at startup
- **THEN** the application MUST refuse to start (fatal error, not warning)
