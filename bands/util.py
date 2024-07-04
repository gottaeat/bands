import urllib.request


def get_url(url, tls_context=None):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    ua += "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": ua},
    )

    if tls_context:
        with urllib.request.urlopen(request, context=tls_context) as f:
            data = f.read()
    else:
        with urllib.request.urlopen(request) as f:
            data = f.read()

    try:
        data = data.decode(encoding="UTF-8")
    except UnicodeDecodeError:
        data = data.decode(encoding="latin-1")

    if len(data) == 0:
        raise ValueError("empty data returned")

    return data
