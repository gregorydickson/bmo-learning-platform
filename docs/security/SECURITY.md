# Security Overview - BMO Learning Platform

## Security Architecture

### Layer 1: Application Security

**LLM Safety Guards**
- Constitutional AI validation for financial content
- PII detection and automatic redaction
- Content moderation via OpenAI API
- Input sanitization and validation
- Output filtering for sensitive data

**API Security**
- Rate limiting (60 requests/minute default)
- Input validation with Pydantic v2
- SQL injection prevention (ORM usage)
- XSS protection (content escaping)
- CSRF protection (Rails built-in)

**Authentication & Authorization**
- JWT-based authentication (Devise)
- Role-based access control (Pundit)
- API key rotation
- Session management
- Password hashing (bcrypt)

### Layer 2: Infrastructure Security

**Network Security**
- VPC with public/private subnets
- Security groups (principle of least privilege)
- Network ACLs
- Private subnet for databases
- NAT gateways for outbound traffic

**Data Encryption**
- TLS 1.3 for data in transit
- RDS encryption at rest (AES-256)
- S3 bucket encryption
- Secrets Manager for credentials
- Redis encryption enabled

### Layer 3: Monitoring & Detection

**Security Monitoring**
- CloudWatch for log aggregation
- Failed authentication tracking
- Anomaly detection
- API rate limit violations
- Unusual access patterns

**Incident Response**
- Automated alerting
- Incident response playbook
- Backup and recovery procedures
- Data breach notification process

## Compliance

### GDPR Considerations

**Data Minimization**
- Collect only necessary learner data
- PII redaction in logs
- Automated data retention policies
- Right to be forgotten support

**Consent Management**
- Explicit opt-in for communications
- Granular consent preferences
- Audit trail for consent changes

### SOC 2 Alignment

**Security Controls**
- Access control policies
- Encryption standards
- Vulnerability management
- Incident response procedures
- Change management

**Availability Controls**
- Multi-AZ deployment
- Automated backups
- Disaster recovery plan
- SLA monitoring

## Vulnerability Management

### Scanning Schedule
- **Daily**: Dependency scanning (Dependabot)
- **Weekly**: Container image scanning (Trivy)
- **Monthly**: Penetration testing
- **Quarterly**: Third-party security audit

### Remediation SLAs
- **Critical**: 24 hours
- **High**: 7 days
- **Medium**: 30 days
- **Low**: 90 days

## Security Testing

### Automated Security Testing
- SAST (Static Analysis): Brakeman, Bandit
- DAST (Dynamic Analysis): OWASP ZAP
- SCA (Dependency Scanning): Trivy, Dependabot
- Secret Scanning: Gitleaks, detect-secrets

### Manual Security Testing
- Quarterly penetration testing
- LLM jailbreak testing
- Prompt injection testing
- API fuzzing
- Social engineering simulations

## Security Contacts

**Security Team**: security@example.com
**Incident Response**: incidents@example.com
**Bug Bounty**: https://bugcrowd.com/bmo-learning

## Reporting Vulnerabilities

Please report security vulnerabilities to security@example.com with:
- Detailed description
- Steps to reproduce
- Potential impact
- Suggested remediation (if applicable)

We commit to:
- Acknowledge within 24 hours
- Provide initial assessment within 72 hours
- Regular updates on remediation progress
