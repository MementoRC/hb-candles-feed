# Security Policy

## Supported Versions

We actively support the following versions of hb-candles-feed with security updates:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of hb-candles-feed seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### How to Report a Security Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories** (Preferred):
   - Go to our [Security Advisories page](https://github.com/MementoRC/hb-candles-feed/security/advisories)
   - Click "Report a vulnerability"
   - Fill out the form with details about the vulnerability

2. **Email**: Send an email to `claude.rc@gmail.com` with the subject line "Security Vulnerability Report"

### What to Include in Your Report

Please include the following information in your vulnerability report:

- **Type of issue** (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- **Full paths of source file(s)** related to the manifestation of the issue
- **The location of the affected source code** (tag/branch/commit or direct URL)
- **Any special configuration required** to reproduce the issue
- **Step-by-step instructions** to reproduce the issue
- **Proof-of-concept or exploit code** (if possible)
- **Impact of the issue**, including how an attacker might exploit the issue

### Response Timeline

We will acknowledge receipt of your vulnerability report within **48 hours** and will send a more detailed response within **7 days** indicating the next steps in handling your report.

After the initial reply to your report, we will endeavor to keep you informed of the progress towards a fix and may ask for additional information or guidance.

## Security Update Process

1. **Assessment**: We will assess the vulnerability and determine its impact and severity
2. **Fix Development**: We will develop a fix for the vulnerability
3. **Testing**: The fix will be thoroughly tested to ensure it resolves the issue without introducing new problems
4. **Release**: We will release a security update and publish a security advisory
5. **Disclosure**: We will coordinate disclosure of the vulnerability details

## Security Best Practices for Users

When using hb-candles-feed, please follow these security best practices:

### API Keys and Credentials
- **Never hardcode API keys** in your source code
- **Use environment variables** to store sensitive configuration
- **Rotate API keys regularly** and immediately if compromised
- **Use read-only API keys** when possible

### Network Security
- **Use HTTPS/WSS connections** for all exchange communications
- **Validate SSL certificates** and avoid disabling certificate verification
- **Monitor network traffic** for unusual patterns
- **Use rate limiting** to prevent abuse

### Code Security
- **Keep dependencies updated** using our automated Dependabot updates
- **Review security advisories** for dependencies regularly
- **Use static analysis tools** like the ones in our CI pipeline
- **Follow secure coding practices** when extending the library

### Data Protection
- **Sanitize sensitive data** in logs and error messages
- **Encrypt sensitive data** at rest and in transit
- **Implement proper access controls** for data storage
- **Regular security audits** of your implementations

## Security Features

hb-candles-feed includes several built-in security features:

### Automated Security Scanning
- **CodeQL analysis** for vulnerability detection
- **Dependency scanning** with Safety and Bandit
- **Secret detection** to prevent credential leaks
- **Weekly security scans** via GitHub Actions

### Secure Defaults
- **HTTPS/WSS only** connections to exchanges
- **Request signing** for authenticated API calls
- **Rate limiting** to prevent API abuse
- **Input validation** for all external data

### Monitoring and Logging
- **Structured logging** with security event tracking
- **Performance monitoring** to detect anomalies
- **Error tracking** without exposing sensitive data
- **Audit trails** for administrative actions

## Vulnerability Disclosure Policy

We believe in responsible disclosure and will work with security researchers to:

1. **Acknowledge** your contribution to improving our security
2. **Provide credit** in our security advisories (if desired)
3. **Coordinate disclosure** to minimize impact on users
4. **Share lessons learned** to improve the broader ecosystem

## Security Resources

- [GitHub Security Features](https://docs.github.com/en/code-security)
- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [Python Security Best Practices](https://python.org/dev/security/)
- [Exchange API Security Guidelines](https://docs.python.org/3/library/hashlib.html)

## Contact Information

For general security questions or concerns:
- **Email**: claude.rc@gmail.com
- **GitHub Issues**: For non-sensitive security discussions only
- **Security Advisories**: For vulnerability reports

---

**Note**: This security policy is regularly reviewed and updated. Please check back periodically for changes.

Last updated: June 2025
