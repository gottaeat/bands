import urllib.request


def get_url(url):
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    ua += "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": ua},
    )

    data, err_msg = None, None

    try:
        with urllib.request.urlopen(request) as f:
            data = f.read()
    except Exception as exc:
        err_msg = exc

    try:
        data = data.decode(encoding="UTF-8")
    except UnicodeDecodeError:
        try:
            data = data.decode(encoding="latin-1")
        except:
            data = None
            err_msg = ValueError("decode failure")
    except Exception as exc:
        data = None
        err_msg = exc

    if len(data) == 0 and err_msg is None:
        data = None
        err_msg = ValueError("empty data returned")

    return data, err_msg
