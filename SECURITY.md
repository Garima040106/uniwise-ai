# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Uniwise AI, **please do not open a public issue**. Instead, email your findings to **security@uniwise.ai** with:

- **Description**: What is the vulnerability?
- **Location**: Which file(s) are affected?
- **Impact**: How could this be exploited?
- **Proof of Concept**: Steps to reproduce (if possible)
- **Suggested Fix**: Do you have a fix?

**We appreciate responsible disclosure and will:**
- Acknowledge receipt within 48 hours
- Provide a timeline for patching
- Credit you in the security advisory (unless you prefer anonymity)

---

## Security Practices

Our security controls include:

### Authentication & Authorization
- ✅ RBAC with fine-grained permissions
- ✅ CSRF protection on all state-changing endpoints
- ✅ Password hashing with PBKDF2
- ✅ Optional 2FA support

### Data Protection
- ✅ HTTPS/TLS for all transmissions
- ✅ SQL parameterized queries (ORM-enforced)
- ✅ File upload validation and scanning
- ✅ User data encryption at rest (configurable)

### Infrastructure
- ✅ Environment variable isolation
- ✅ Dependency scanning and updates
- ✅ Rate limiting to prevent abuse
- ✅ API audit logging for compliance

### Development
- ✅ Code review on all PRs
- ✅ Dependency vulnerability scanning (Dependabot)
- ✅ SAST/DAST as part of CI/CD pipeline
- ✅ Regular security updates

---

## Supported Versions

| Version | Supported          | Notes                      |
|---------|-------------------|--------------------------|
| 0.3.0+  | ✅ Yes            | Latest, fully supported  |
| 0.2.x   | ⚠️ Limited        | Security fixes only      |
| 0.1.x   | ❌ No             | Upgrade recommended      |

---

## Known Issues & Mitigations

### Current
None known at this time.

### Past (Fixed)
- **CVE-XXXX-XXXXX** (v0.2.5): Token expiration issue → Fixed in v0.2.6
- **Dependency**: Old Django version → Updated to 4.2 LTS

See [CHANGELOG.md](CHANGELOG.md) for details.

---

## Security Checklist for Deployment

If you're running Uniwise AI in production, ensure:

```
[ ] DEBUG = False in production settings
[ ] SECRET_KEY is long, random, and unique
[ ] ALLOWED_HOSTS configured correctly
[ ] Database password is strong (16+ chars, no dictionary words)
[ ] TLS/SSL certificates are valid and current
[ ] Email credentials use app-specific passwords (not master password)
[ ] Redis is password-protected if exposed to network
[ ] Firewall restricts database access to app servers only
[ ] Regular backups configured (encrypted)
[ ] Log monitoring and alerts are enabled
[ ] CORS origins are explicitly whitelisted
[ ] Rate limiting is enabled
[ ] WAF (Web Application Firewall) rules are active
[ ] Dependencies are regularly updated
[ ] HTTPS enforced (SECURE_SSL_REDIRECT = True)
```

---

## Upcoming Security Features

- [ ] SCIM 2.0 for user provisioning
- [ ] Hardware security key support
- [ ] Advanced threat detection with ML
- [ ] Compliance dashboards (HIPAA, GDPR, FERPA)

---

For more information, see [Deployment Guide](docs/DEPLOYMENT.md) and [Contributing Guidelines](CONTRIBUTING.md).

**Last Updated**: March 2026
