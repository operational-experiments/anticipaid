# Deploy Anticipaid

## GitHub Pages

1. Repository → **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Under **Custom domain**, enter `anticipaid.com` and save.
4. After DNS resolves and GitHub provisions the certificate, enable **Enforce HTTPS**.

## DNS

Create these records at the authoritative DNS provider for `anticipaid.com`:

| Type | Name | Value |
|---|---|---|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |
| CNAME | www | operational-experiments.github.io |

Optional IPv6 records:

| Type | Name | Value |
|---|---|---|
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |

Remove conflicting parking/hosting `A`, `AAAA`, `ALIAS`, or `ANAME` records at `@`, and any conflicting `www` record.

## Refresh behavior

The workflow rebuilds the public market snapshot every four hours. It does not commit generated data back to `main`; each scheduled run creates and deploys a fresh Pages artifact.
