#!/usr/bin/env python
"""
Startup wrapper for uvicorn to avoid DNS resolution issues with 0.0.0.0
"""

import uvicorn

if __name__ == "__main__":
    # Use None as host to bind to all interfaces without DNS resolution
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        workers=1,
        timeout_keep_alive=75,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
