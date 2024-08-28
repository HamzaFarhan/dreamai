# Acme Inc IT Security Policy

## Access Control
- All users are assigned unique user IDs and passwords. Sharing of accounts is strictly prohibited. 
- Passwords must be at least 12 characters long and include uppercase, lowercase, numbers and symbols. Passwords expire every 90 days. Previous 12 passwords cannot be reused.
- Multi-factor authentication (MFA) is required for all remote access to company systems, cloud services, and privileged accounts.
- User access is granted based on least privilege and job responsibilities. Access is reviewed quarterly and immediately revoked upon role change or termination.
- Privileged access requires management approval and use of a separate admin account. Admin activities are logged and monitored.
- Third-party access requires management approval and must use MFA. Access is disabled when no longer needed.

## Data Protection 
- Customer data is classified as confidential and access restricted to authorized personnel. 
- Data is encrypted in transit using TLS 1.2+ and at rest using AES-256. Encryption keys are managed in an HSM.
- Access to customer data is logged and monitored using a SIEM. Anomalous activity alerts are investigated.  
- Databases and file shares hosting sensitive data require MFA and are segregated in the network.
- Confidential data is not permitted on removable media without encryption and management approval. 
- Backups are encrypted and stored in a geographically separate data center. Backup restores are tested quarterly. Backups are retained for 1 year.
- Data is securely wiped from devices prior to reuse or disposal using DoD 5220.22-M methods. Certification of destruction is obtained.

## Network Security
- Network is segmented using firewalls to restrict traffic between security zones. Firewall rules are reviewed quarterly.
- Remote access requires use of an approved VPN with MFA. VPN is restricted to company-managed devices running EDR.
- Intrusion detection/prevention systems are used to monitor network traffic for malicious activity.
- All systems run anti-malware software with daily definition updates and real-time scanning.
- All systems, appliances and applications are hardened per industry benchmarks (CIS, NIST). 
- Security patches are deployed monthly or sooner for critical vulnerabilities, prioritizing externally exposed systems.
- Internal and external vulnerability scanning is conducted monthly. Critical vulnerabilities are remediated within 30 days.
- Penetration testing is conducted quarterly by an independent third party. Findings are triaged and remediated based on risk.
- Web application firewalls are used for public-facing web applications.
- A CASB monitors all cloud service usage for data exfiltration and anomalous activity.

## Endpoint Security
- All workstations and laptops run centrally managed EDR/MDR with logging enabled. 
- Full disk encryption is required using BitLocker (Windows) or FileVault (Mac).
- USB ports are restricted. Only approved devices permitted.
- Software installation is restricted. Users cannot disable security software.
- Screen locks are enforced after 10 minutes of inactivity.

## Physical Security
- Access to offices, data centers and wiring closets is restricted to authorized personnel using badge readers and PINs.
- Doors automatically close and lock. Badge activity is logged and monitored.
- Visitors must sign a log, wear a badge, and be escorted at all times.
- Offices use 24/7 monitored alarm systems with security cameras at entry/exit points.
- Environmental controls include redundant commercial power, UPS, generators, and fire suppression systems. 
- Wiring is enclosed in conduit. Redundant ISP connections are used.

## Incident Response
- A formal incident response plan is maintained that defines alert severity levels, roles and responsibilities, investigation procedures, containment steps, recovery, and internal/external communication protocols.
- The plan is tested annually in a tabletop exercise and updated based on lessons learned.
- A 24/7 phone number and email alias are provided for reporting suspected incidents. 
- Incident response personnel maintain security clearances and receive annual training.
- Cyber insurance is maintained to cover incident response, forensics, notification costs, etc.

## Asset Management
- A centralized inventory is maintained of all IT hardware and software assets, including physical location, assigned owner, and supported status.  
- New assets are added to inventory upon procurement and removed upon disposal.
- Inventory audits are conducted annually to verify accuracy.
- Unsupported systems are not permitted on the network unless isolated and necessary for business. A remediation plan is required.

## Risk Management
- A steering committee of senior leadership meets quarterly to review top risks to information assets.
- An annual risk assessment is conducted to identify threats/vulnerabilities and assess risk based on likelihood and impact.
- Risks are treated with security controls or accepted by management where risk exceeds risk appetite.

## HR Security
- Background checks are conducted for new hires in accordance with local laws, including criminal history and employment verification.
- Employees sign a confidentiality agreement covering data protection and IP.
- Employees complete mandatory annual training on acceptable use, data handling and reporting security incidents.
- Disciplinary procedures are enforced for policy violations up to termination.

## Compliance
- Acme Inc certifies compliance with applicable industry standards, e.g. PCI DSS, SOC 2, ISO 27001, HIPAA. 
- Audits are conducted annually by an independent assessor. Audit findings are remediated.
- A compliance manager monitors relevant laws and regulations for changes.

## Policy Management
- This policy is reviewed and updated annually and upon significant changes.
- Supporting control procedures are maintained by asset owners.
- Policy exceptions require CISO approval and are reviewed annually.  
- Employees certify acknowledgement of this policy annually.



# Acme Inc Employee Security Policy

## Acceptable Use
- Company resources are for business use only. Personal use is prohibited. 
- Users must comply with applicable laws and regulations. Illegal content and copyright infringement are prohibited.
- Users must not attempt to circumvent security controls, access confidential data without authorization, or install unauthorized software/hardware.

## Confidentiality
- Employees must protect confidential company information from unauthorized disclosure.
- Confidential data must not be shared with external parties without an NDA. 
- Confidential data must not be posted publicly or stored on unapproved cloud services.
- Confidential hard copy documents must be shredded when no longer needed.

## Data Handling  
- Data must be classified based on sensitivity and labelled.
- Need to know and least privilege principles must be followed.
- Customer PII and cardholder data must be encrypted in transit and at rest.
- PII must only be collected and used with consent and for the specified purpose.

## Secure Development
- All code must be tested for vulnerabilities before production release.
- OWASP Top 10 risks must be mitigated.
- Secrets must not be hardcoded. A secrets management solution must be used.
- Open source code must come from trusted sources. SCA tools must be used to scan for vulnerabilities.

## Physical Security
- Employees must wear a badge on premises.
- Visitors must be logged and escorted.
- Sensitive areas must remain locked.
- Employees must not tailgate through secure doors.

## Workstation Security  
- Workstations must not be left unattended. Screens must be locked when not in use.
- MFA must be used.  
- Workstations must run current AV and be patched within 30 days.
- Full disk encryption must be enabled.
- Files must be stored on network shares, not locally.
- Clear desk policy must be followed.

## Remote/Mobile
- Company laptops and mobile devices must be used to access company data. 
- MFA and VPN must be used for remote access.
- Public wifi must not be used without the VPN.
- Laptops and mobile devices must be physically secured at all times.
- Lost/stolen devices must be reported immediately.

## Incident Reporting
- Employees must immediately report security incidents by calling the security hotline or emailing security@acme.com.
- Incidents include malware, unauthorized account usage, data loss/theft, and physical security breaches.
- Employees must not attempt to investigate on their own.

## Privacy
- Employees must not access or disclose customer or employee personal data without authorization.
- Employees must complete data privacy training before accessing PII.
- Marketing must honor opt-out requests.

## Disciplinary Action
- Violation of this policy may result in disciplinary action up to and including termination.
- Employees must report violations to their manager or HR.



# Acme Inc Business Continuity and Disaster Recovery Plan

## Program Governance
- The BC/DR program is sponsored by the COO with oversight from a steering committee of senior leadership.
- The program is managed by the BC/DR Manager with support from IT, HR, facilities, and business units.
- A BC/DR policy established program requirements, roles and responsibilities, and KPIs.

## Business Impact Analysis 
- A BIA is conducted annually by interviewing business process owners. 
- The BIA identifies critical processes, resources, dependencies, and financial/operational impacts of a disruption over time. 
- Maximum tolerable downtime (MTD) and recovery time objectives (RTO) are determined for each process.
- Critical vendors are identified and recovery requirements defined in contracts.

## Risk Assessment
- A risk assessment is conducted annually to identify and assess natural and man-made threats to business operations.
- Risks are scored based on likelihood and impact to people, property, technology and reputation. 
- Risk treatment options are evaluated including new controls, alternate suppliers or sites, and risk transfer.

## Strategy
- Critical processes are recovered in priority order based on RTOs and dependencies. Non-critical processes are deferred until resources permit.
- Primary systems and data are replicated in near real-time to a hot DR site in a separate region using a dedicated network link.
- Alternate office space and equipment are pre-staged under contract to enable quick activation and relocation. Mobile recovery units are available if needed.
- SaaS and cloud infrastructure are used where possible to increase resiliency. Failover is tested monthly.
- Employees are equipped to work remotely via secure laptops and VDI. Capacity is monitored.

## Plan
- The BC/DR plan documents process RTOs, recovery sequence, roles and responsibilities, notification procedures, alternate site locations, and detailed recovery procedures.
- Plans are maintained for loss of facility, technology, suppliers, and people (pandemic).
- Call trees are maintained with primary and secondary contacts for crisis management, recovery teams, employees, customers and public authorities.
- Failover procedures are documented for network rerouting, DNS updates, etc.

## Exercising
- Walkthrough exercises are conducted quarterly with recovery teams to validate roles and procedures.
- Annual functional exercises are conducted with business teams to test alternate operations, e.g. paper processing, manual workarounds, and team coordination. 
- A full interruption test is conducted annually rotating between loss scenarios (facility, data center, etc.) Failover to the DR site and reconstitution to production is performed.
- After-action reviews are conducted to document lessons learned and update plans. KPIs are measured and reported to management.

## Continuous Improvement  
- Recovery capabilities are re-evaluated after significant business or technology changes. 
- New products and services require BC/DR plans before launch.
- Supply chain resiliency is reviewed annually including sole-source suppliers, geopolitical risk and transportation risk.
- Information feeds from threat intelligence services and public agencies are monitored for emerging threats.
- Budget and staffing for the BC/DR program are reviewed annually as part of the business planning cycle.



# Acme Inc Vendor Management Policy

## Governance
- A vendor management office (VMO) is established within procurement to govern vendor relationships.
- The VMO maintains policies and procedures for vendor selection, contracting, onboarding, performance management, and offboarding.
- Vendor risk is overseen by the risk committee and CISO. High risk vendors require CISO approval.
- An approved vendor list is maintained with risk ratings, spend tier, and primary contacts.

## Due Diligence
- RFP/RFIs must include security and privacy requirements. Vendor responses are evaluated by infosec.
- Vendors are screened through public records, financial reports, D&amp;B reports, reference checks, etc.
- A vendor security assessment is conducted using industry standard questionnaires (e.g. SIG, CAIQ). Responses are validated on site for high risk vendors.
- Vendors processing confidential data are assessed for compliance with regulatory standards (PCI, HIPAA, GDPR, etc.). Evidence of compliance is obtained. 
- Vendors are assigned an inherent risk rating based on access to data, business criticality, and outsourced controls. Risk ratings are reviewed annually.

## Contracting
- Contracts include security and privacy terms such as compliance requirements, right to audit, security incident notification, data ownership, and termination rights.
- Data protection addendums and business associate agreements are required where applicable.  
- Contracts specify service levels (SLA), recovery time objectives (RTO), and penalties for non-performance.
- Contracts define the process to receive vulnerability reports and remediate vendor products.
- Source code escrow is required for critical solutions.

## Onboarding
- Upon contract signing, vendors are provisioned in procurement and AP systems.
- Security configurations are applied prior to granting access to systems and data.
- Secure data transfer methods are established for data exchanges.

## Ongoing Management
- Vendor performance to SLAs is monitored, including security metrics. Dashboards are reviewed monthly.
- High risk vendors provide independent audit reports annually (SOC 2, ISO 27001, PCI ROC, etc.)
- Material changes to vendor's security posture or breach history are reviewed for increased risk.
- Vulnerability scan data is obtained monthly for hosted/cloud vendors. 
- Business continuity and DR plans are obtained annually and tested where feasible.
- Vendor security incidents are scored for impact and root cause is determined. The VMO participates in after-action reviews.

## Termination
- Upon contract termination, access is revoked, data is returned or destroyed, and equipment is returned.
- A service transition plan is enacted to prevent disruption, including knowledge transfer and migration to a new solution/vendor.
- Final invoices are paid and vendor records are archived per record retention policy.
- Lessons learned are documented and factored into future sourcing decisions.



# Acme Inc Application Security Standards

## Secure SDLC
- Projects must follow the approved SDLC including security requirements, threat modeling, secure coding, code review and testing.
- The security champion reviews user stories for security impact and participates in design reviews.
- All code changes require peer review. Merges to the main branch require 2 approvals.
- Major releases require signoff from the security architect.
- DevSecOps tools are used to automate security scans including SAST, DAST, SCA and container scanning. Builds fail if high severity issues are found.

## Authentication
- Applications must not accept credentials in URLs or logs.
- MFA is required for admin access and business critical apps. FIDO2 or push notification is preferred.
- Service accounts must not be shared. Passwords must be vaulted and rotated every 90 days.
- Authentication failures are logged. Accounts are locked after 5 failed attempts for 30 minutes.
- Forgot password flows use time-bound secure token sent via a side channel.

## Session Management
- Stateless JWT access and refresh tokens must be used, not server-side sessions.
- JWTs must be signed using the RS256 alg. HS256 is prohibited.
- The access token must be short-lived (5-10 min). The refresh token expires in 8 hours.  
- Refresh tokens are only sent to the token endpoint. Access tokens are not stored.
- Refresh tokens are invalidated on logout. Tokens are single use.

## Access Control
- Roles and permissions are defined using RBAC. Access is granted to roles, not users.
- Roles are reviewed quarterly and follow least privilege. 
- Fine-grained, feature level permissions are used for sensitive functions.
- The application enforces access control on every request. Access failures return "403 Forbidden".
- DOM-based access control is not used.  
- API endpoints authorize the calling application and token.

## Input Validation
- All input is untrusted and must be validated for type, length, format and range.
- Validation is performed on the server. Client-side validation is only for UX.
- Data is normalized and output encoded to prevent XSS, SQL injection and other injection flaws.
- Parameterized queries or ORM frameworks are used.
- SSRF protections are in place. URL whitelisting, DNS resolution and response filtering are used.
- XML input is validated against XXE using a local static DTD.
- Deserialization of untrusted data is prohibited.

## File Uploads
- Only allow whitelisted file types. Validate type by inspecting file headers, not extension.
- Set a max file size to prevent large files from overwhelming the system.
- Generated filenames should not use user input.
- Files must be scanned by AV before being stored or opened.
- File downloads should use the Content-Disposition: attachment header.

## Cryptography
- Don't roll your own crypto. Only use approved crypto libraries.  
- Use authenticated encryption modes (GCM). Avoid unauthenticated (CBC).
- 2048-bit or larger RSA keys and 256-bit or larger ECC keys must be used.
- Secrets must be generated using a CSPRNG.
- Password storage must use Argon2, PBKDF2, scrypt or bcrypt.

## Error Handling  
- Exceptions must be caught and handled gracefully.
- Fail securely. Denied access should return a generic 403 error.
- Sensitive data must not be logged or returned in error messages.  
- Use HTTP 400-series for client errors, 500-series for server errors.

## Logging
- Log authentication events, access control failures, input validation failures and exceptions.
- Include timestamp, username, IP address, and detailed event info.
- Log to a separate server. Restrict access to logs.
- Disallow sensitive data in logs. Mask or truncate as needed.

## Response Headers
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- Content-Security-Policy with strict policies
- Strict-Transport-Security with min 1 year max-age  
- Cache-Control, Pragma: no-cache on sensitive pages

