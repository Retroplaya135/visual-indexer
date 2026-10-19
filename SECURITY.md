# Security

Retrieval requires explicit operator confirmation and an allowed host. The host rule includes subdomains. The fetcher rejects URL credentials, non-HTTP schemes, ports other than 80 or 443, non-public DNS answers, oversized responses, and unsupported page content types. Redirects receive the same address and host checks and are limited to four hops by default.

The fetcher checks robots policy for the requested URL before fetching the page. It does not separately evaluate robots policy for every redirect destination. Empty or denying robots policies stop the initial request. Output paths are checked against the selected output directory.

Connections use a policy-validated IP address directly. HTTPS still verifies the authorized hostname through TLS Server Name Indication, which avoids a second unvalidated DNS lookup between policy evaluation and connection establishment.

Report suspected vulnerabilities privately to the repository owner with a synthetic reproduction. Do not attach third-party pages, cookies, credentials, browser profiles, or downloaded media.
