# OpenCode Agent Instructions & Proxy Configuration

## 🌐 Network & Proxy Setup (T-Systems Network)
In this environment, all external HTTP/HTTPS requests (GitHub API, PyPI, Git fetch/push) require the corporate proxy server:
- **Proxy URL:** `http://10.36.152.6:3128` (Backup: `http://10.36.153.4:3128`)

### Environment Variables
The `.env` file in this directory automatically supplies:
```env
HTTP_PROXY=http://10.36.152.6:3128
HTTPS_PROXY=http://10.36.152.6:3128
http_proxy=http://10.36.152.6:3128
https_proxy=http://10.36.152.6:3128
NO_PROXY=localhost,127.0.0.1,.t-internal.com
```

### Git & GitHub CLI Usage
1. **Git Config:** Git has been configured with `http.proxy` and `https.proxy` set to `http://10.36.152.6:3128`.
2. **GitHub Token:** Token is located in `github-token.txt` (or `../github-token.txt`). Before running `gh` CLI commands, set `GH_TOKEN`:
   - PowerShell: `$env:GH_TOKEN = (Get-Content "..\github-token.txt").Trim()`
   - Bash/CMD: `export GH_TOKEN=$(cat ../github-token.txt)`
3. **gh auth setup-git:** Run `gh auth setup-git` to pass credentials to git commands.

### Python / Pip Usage
When running `pip` or Python scripts making network requests, ensure proxy parameters or environment variables are inherited:
```bash
pip install --proxy http://10.36.152.6:3128 -r requirements.txt
```
