# Release checklist

Status as of 2026-09-08: **local candidate; publication blocked**.

- [ ] The owner confirms rights to publish the code, generated trial tables and documentation.
- [ ] The owner confirms the repository name and hosting account.
- [ ] The owner confirms MIT as the license for this exact release.
- [x] The candidate snapshot contains no email address, account handle, local absolute path or cloud instance identifier.
- [x] No customer, account, market, growth-operation or real-robot data is included.
- [x] The included executable code uses the Python standard library only.
- [x] Frozen CSV hashes and decision gates are checked automatically.
- [x] ExecutionEvidence has an end-to-end replay and ten focused unit tests.
- [x] README states purpose, minimum command, evidence boundary and maintenance status.
- [x] A clean-directory reproduction check has been run locally.
- [ ] A complete secret scan must be rerun after the final commit exists.
- [ ] The final Git history and generated GitHub diff must be reviewed.
- [ ] The exact public repository URL and final commit must be shown for explicit approval.

No remote may be added and no repository may be created or pushed while any
unchecked item remains.
