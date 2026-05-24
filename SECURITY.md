# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < main  | :x:                |

**Note**: This project follows a continuous deployment model. The `main` branch is always the latest supported version.

## Reporting a Vulnerability

We take the security of Footy Tipping seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please Do Not

- **Do not** open a public GitHub issue for security vulnerabilities
- **Do not** disclose the vulnerability publicly until it has been addressed

### Please Do

1. **Email the maintainer** at the email address listed in the repository
2. **Provide detailed information** including:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if you have one)

### What to Expect

- **Acknowledgment**: We will acknowledge receipt of your vulnerability report within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Fix timeline**: We will work to fix the vulnerability as quickly as possible
  - **Critical**: Within 7 days
  - **High**: Within 14 days
  - **Medium**: Within 30 days
  - **Low**: Within 60 days
- **Disclosure**: We will coordinate with you on public disclosure timing

## Security Update Policy

### Automated Dependency Updates

- **Dependabot**: Enabled for automated security updates
- **Review process**: Security updates are reviewed and merged promptly
- **Testing**: All updates must pass CI checks before merging

### Manual Security Reviews

We conduct security reviews:
- Before major releases
- When adding new dependencies
- When modifying authentication or data handling
- Quarterly as part of maintenance

## Security Best Practices

This project follows these security practices:

### Code Security

- **No secrets in code**: All secrets stored in environment variables
- **Input validation**: All user inputs are validated
- **Output encoding**: All outputs are properly encoded
- **Dependency scanning**: Regular scans for vulnerable dependencies

### API Security

- **Edge runtime**: API routes run on Vercel Edge Network
- **Rate limiting**: Implemented via Vercel
- **CORS**: Properly configured for API routes
- **Error handling**: No sensitive information in error messages

### Data Security

- **No PII storage**: No personally identifiable information stored
- **localStorage only**: User picks stored client-side only
- **No authentication**: No user accounts or passwords
- **Public data**: All data is public NRL information

### Infrastructure Security

- **HTTPS only**: All traffic encrypted via Vercel
- **Environment variables**: Secrets stored in Vercel environment
- **Branch protection**: Main branch protected, requires PR reviews
- **CI/CD security**: GitHub Actions with minimal permissions

## Known Security Considerations

### Current Architecture

This project uses a serverless architecture with baked JSON data:

- **No database**: Reduces attack surface
- **Static files**: Served via CDN, minimal server-side processing
- **Client-side state**: User picks stored in localStorage (not sensitive)
- **Public API**: Live override API is public (no authentication needed)

### Potential Risks

1. **API key exposure**: `ODDS_API_KEY` must be kept secret
   - Stored in GitHub Secrets
   - Never committed to repository
   - Rotated if compromised

2. **Data integrity**: Baked JSON files could be tampered with
   - Mitigated by branch protection
   - All changes via PR with CI checks
   - Automated bot commits are auditable

3. **Client-side manipulation**: Users can modify localStorage picks
   - Acceptable: No server-side validation needed
   - Picks are for personal use only
   - No competitive or monetary value

## Security Checklist for Contributors

When contributing, ensure:

- [ ] No secrets or API keys in code
- [ ] No sensitive data in logs or error messages
- [ ] Input validation for all user inputs
- [ ] Proper error handling (fail-soft)
- [ ] Dependencies are up to date
- [ ] No new security warnings from `npm audit`
- [ ] No SQL injection risks (N/A - no database)
- [ ] No XSS risks (React escapes by default)
- [ ] No CSRF risks (no authentication)

## Vulnerability Disclosure Timeline

1. **Day 0**: Vulnerability reported
2. **Day 1-2**: Acknowledgment sent to reporter
3. **Day 3-7**: Vulnerability assessed and fix developed
4. **Day 7-14**: Fix tested and deployed
5. **Day 14+**: Public disclosure coordinated with reporter

## Security Tools

We use the following tools to maintain security:

- **npm audit**: Scans for vulnerable npm packages
- **Dependabot**: Automated dependency updates
- **GitHub Security Advisories**: Monitors for known vulnerabilities
- **ESLint security plugins**: Static analysis for common issues
- **TypeScript strict mode**: Catches type-related bugs

## Contact

For security concerns, please contact:
- **GitHub**: Open a security advisory (preferred)
- **Email**: See repository maintainer's profile

## Acknowledgments

We appreciate the security research community and will acknowledge reporters (with permission) when vulnerabilities are disclosed.

---

Last updated: 2025-01-15
