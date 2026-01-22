# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | ✅ Yes             |
| 0.1.x   | ✅ Yes (with delay)|
| < 0.1   | ❌ No              |

## Reporting a Vulnerability

**Please do NOT open a public issue to report a vulnerability.**

Instead, please email security@example.com (or use GitHub's private vulnerability reporting) with:

- Description of the vulnerability
- Affected version(s)
- Impact assessment
- Suggested fix (if available)

We will acknowledge receipt within 48 hours and provide a status update within 7 days.

## Security Best Practices

### For Users

1. **Keep Dependencies Updated**: Run `pip install --upgrade -r requirements.txt` regularly
2. **Use Virtual Environments**: Always use a virtual environment to isolate dependencies
3. **Limit API Permissions**: Grant only the necessary Gmail API scopes in your configuration
4. **Protect Credentials**: Never commit API keys, tokens, or secrets to version control
5. **Review Logs**: Regularly check logs for suspicious activity

### For Contributors

1. **Code Review**: All code is reviewed before merging, including security implications
2. **Dependency Scanning**: We use `safety` and `pip-audit` to scan for known vulnerabilities
3. **Static Analysis**: `bandit` is used to identify common security issues
4. **Testing**: All contributions must include tests demonstrating correctness
5. **Documentation**: Security-relevant changes must be documented

## Security Tools and Scanning

This project uses the following security tools:

- **bandit**: Scans Python code for common security issues (run via GitHub Actions)
- **safety**: Checks dependencies for known security vulnerabilities
- **pip-audit**: Audits Python packages for known vulnerabilities
- **GitHub Security Tab**: Dependency tracking and vulnerability alerts

### Running Security Checks Locally

```bash
# Install security tools
pip install bandit safety pip-audit

# Run bandit to scan for common security issues
bandit -r src/ -ll

# Check dependencies for vulnerabilities
safety check
pip-audit

# Run pre-commit hooks (includes security checks)
pre-commit run --all-files
```

## Known Issues

### None Currently

If you discover a security vulnerability, please follow the reporting process above.

## Security Updates

- **November 2024**: Initial security policy established
- **November 2024**: Added GitHub Actions security scanning workflow

## Third-Party Dependencies

Critical dependencies and their security monitoring:

| Package | Version | Security Status |
| ------- | ------- | --------------- |
| google-auth | Latest | ✅ Monitored    |
| google-api-client | Latest | ✅ Monitored |
| cryptography | Latest | ✅ Monitored |

All dependencies are scanned on each push and PR via GitHub Actions.

## Contact

For security-related questions or concerns, please email: security@example.com

## Additional Resources

- [Gmail API Security](https://developers.google.com/gmail/api/auth)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security_warnings.html)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
