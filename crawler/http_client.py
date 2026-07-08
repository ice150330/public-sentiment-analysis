"""Shared HTTP helpers for crawler modules."""

import logging
import os

import requests
import urllib3
from requests.exceptions import SSLError
from urllib3.exceptions import InsecureRequestWarning

logger = logging.getLogger(__name__)


def _prefer_utf8(response: requests.Response) -> requests.Response:
    if not response.encoding or response.encoding.lower() in {"iso-8859-1", "latin-1"}:
        response.encoding = "utf-8"
    return response


def get(url: str, **kwargs) -> requests.Response:
    """GET with a local-dev SSL fallback for public crawler endpoints.

    Some Windows/Python installs lack the root certificates needed by requests.
    We keep normal TLS verification first, then retry once with verification off
    only for certificate-chain failures. Set CRAWLER_ALLOW_INSECURE_SSL_FALLBACK=false
    to disable the fallback.
    """
    allow_fallback = os.getenv("CRAWLER_ALLOW_INSECURE_SSL_FALLBACK", "true").lower() not in {
        "0",
        "false",
        "no",
    }

    try:
        return _prefer_utf8(requests.get(url, **kwargs))
    except SSLError as exc:
        if not allow_fallback or "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise

        logger.warning("SSL certificate verification failed for %s; retrying without verification", url)
        urllib3.disable_warnings(InsecureRequestWarning)
        return _prefer_utf8(requests.get(url, verify=False, **kwargs))
