#!/usr/bin/env python3
"""yt-dlp CLI sarmalayıcısı — bozuk yerel ISP GGC (googlevideo.com) düğümleri için otomatik yedek geçişi.

Bazı ISP'lerin yerel Google Global Cache (GGC) düğümleri TLS/SSL el sıkışmasında
([SSL: INVALID_SESSION_ID] / Connection reset) başarısız olurken, YouTube'un URL içindeki
`mn=` parametresinde verdiği ikinci (yedek) googlevideo.com düğümü sorunsuz çalışır.
Tarayıcı oynatıcısı bu yedeğe otomatik geçer; yt-dlp geçmez. Bu sarmalayıcı,
transport/SSL hatası alındığında aynı yedeğe (fallback_count=1) otomatik geçer.
"""
import re
import sys
import urllib.parse

import yt_dlp
from yt_dlp.networking.exceptions import HTTPError, TransportError

_BAD_HOSTS = {}  # {bozuk_netloc: yedek_netloc}


def swap_mn_fallback(url):
    """YouTube googlevideo.com URL'sinde birincil mn düğümünü yedek mn düğümüyle değiştirir."""
    p = urllib.parse.urlparse(url)
    if not p.netloc.endswith(".googlevideo.com"):
        return None

    qs = urllib.parse.parse_qs(p.query, keep_blank_values=True)
    mn_raw = (qs.get("mn") or [""])[0]
    is_path_style = False
    if not mn_raw:
        m = re.search(r"/mn/([^/]+)", p.path)
        if m:
            mn_raw = urllib.parse.unquote(m.group(1))
            is_path_style = True

    mn = [x for x in mn_raw.split(",") if x]
    if len(mn) < 2 or mn[0] not in p.netloc:
        return None

    new_netloc = p.netloc.replace(mn[0], mn[1], 1)
    if is_path_style:
        path = p.path
        if "/fallback_count/" not in path:
            path = path.rstrip("/") + "/fallback_count/1"
        return urllib.parse.urlunparse((p.scheme, new_netloc, path, p.params, p.query, p.fragment))

    q = p.query
    if "fallback_count=" not in q:
        q = (q + "&fallback_count=1") if q else "fallback_count=1"
    return urllib.parse.urlunparse((p.scheme, new_netloc, p.path, p.params, q, p.fragment))


def _set_req_url(req, url):
    if isinstance(req, str):
        return url
    req.url = url
    return req


def _install_ggc_fallback():
    orig_urlopen = yt_dlp.YoutubeDL.urlopen

    def patched_urlopen(self, req):
        u = req if isinstance(req, str) else getattr(req, "url", "")
        if u:
            host = urllib.parse.urlparse(u).netloc
            if host in _BAD_HOSTS:
                fb = swap_mn_fallback(u)
                if fb:
                    req = _set_req_url(req, fb)
                    u = fb
        try:
            return orig_urlopen(self, req)
        except Exception as e:
            if isinstance(e, HTTPError):
                raise
            is_net_err = isinstance(e, (TransportError, OSError)) or any(
                k in str(e).lower()
                for k in ("ssl", "invalid_session_id", "timed out", "connection reset", "10054", "eof")
            )
            if is_net_err and u:
                fb = swap_mn_fallback(u)
                if fb:
                    old_host = urllib.parse.urlparse(u).netloc
                    new_host = urllib.parse.urlparse(fb).netloc
                    _BAD_HOSTS[old_host] = new_host
                    req = _set_req_url(req, fb)
                    return orig_urlopen(self, req)
            raise

    yt_dlp.YoutubeDL.urlopen = patched_urlopen


def main():
    _install_ggc_fallback()
    yt_dlp.main()


if __name__ == "__main__":
    main()
