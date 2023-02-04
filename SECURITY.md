# Security Policy

The kas community takes the security of its code seriously. If you think you
have found a security vulnerability, please read the next sections and follow
the instructions to report your finding.

## Security Context

Open source software can be used in various contexts that may go far beyond
what it was originally designed and also secured for. Therefore, we describe
here how kas is currently expected to be used in security-sensitive scenarios.

In a nutshell, the purpose of kas is fetching known and previously validated
content, identifying it as original, and then configuring and building
artifacts. Therefore, anything that may prevent checking the integrity of
fetched content prior to executing instructions it carries is security-wise in
scope for kas. This affects both the kas tool itself and the containers
provided by kas because they also contain tools that kas or bitbake use for
fetching and validating.

## Reporting a Vulnerability

Please DO NOT report any potential security vulnerability via a public channel
(mailing list, github issue etc.). Instead, create a report via
https://github.com/siemens/kas/security/advisories/new or contact the
maintainer jan.kiszka@siemens.com via email directly. Please provide a detailed
description of the issue, the steps to reproduce it, the affected versions and,
if already available, a proposal for a fix. You should receive a response
within 5 working days. If the issue is confirmed as a vulnerability by us, we
will open a Security Advisory on github and give credits for your report if
desired. This project follows a 90 day disclosure timeline.
