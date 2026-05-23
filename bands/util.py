from urllib.request import build_opener, HTTPRedirectHandler, HTTPSHandler, Request
from urllib.error import HTTPError


# don't follow redirects
class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def get_url(url, extra_headers=None, payload=None, tls_context=None, timeout=10):
    # get response
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
    }

    if extra_headers:
        headers.update(extra_headers)

    request = Request(
        url,
        headers=headers,
        data=payload,
        method="POST" if payload is not None else "GET",
    )

    opener_handlers = [NoRedirectHandler]
    if tls_context is not None:
        opener_handlers.append(HTTPSHandler(context=tls_context))

    opener = build_opener(*opener_handlers)

    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as exc:
        raise ValueError(f"request returned {exc.code} for: {url}") from exc
    except Exception as exc:
        raise ValueError(f"request failed for: {url}") from exc

    with response:
        # handle only 200
        status = response.getcode()
        if status != 200:
            raise ValueError(f"request returned {status} for: {url}")

        # check mimetype
        content_type = response.headers.get("Content-Type")
        if not content_type:
            raise ValueError(f"request missing content-type header: {url}")

        mime_type = content_type.split(";", 1)[0].strip().lower()
        if not mime_type:
            raise ValueError(f"request missing mimetype: {url}")

        allowed_mime_types = {
            "application/javascript",
            "text/javascript",
            "application/json",
            "text/json",
            "text/plain",
            "application/xml",
            "text/xml",
        }
        if (
            mime_type not in allowed_mime_types
            and not mime_type.endswith("+json")
            and not mime_type.endswith("+xml")
        ):
            raise ValueError(f"request contains mimetype {mime_type}: {url}")

        # check size
        content_length = response.headers.get("Content-Length")
        if content_length is None:
            raise ValueError(f"request missing content-length header: {url}")

        try:
            content_length_int = int(content_length)
        except Exception as exc:
            raise ValueError(f"invalid content-length header: {url}") from exc

        if content_length_int <= 0:
            raise ValueError(f"request returned no data: {url}")

        max_bytes = 5242880  # 5m
        if content_length_int > max_bytes:
            raise ValueError(f"content-length >5m: {url}")

        data = response.read(max_bytes + 1)
        if not data:
            raise ValueError(f"request returned no data: {url}")

        if len(data) > max_bytes:
            raise ValueError(f"content-length >5m: {url}")

        encoding = response.headers.get_content_charset() or "utf-8"

        tried = set()
        for candidate_encoding in (encoding, "latin-1"):
            if candidate_encoding in tried:
                continue

            tried.add(candidate_encoding)

            try:
                return data.decode(candidate_encoding)
            except (UnicodeDecodeError, LookupError):
                continue

        raise ValueError(f"unable to decode: {url}")
