import urllib.request


def get_url(url, tls_context=None):
    # set useragent
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    ua += "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": ua},
    )

    # get response
    # pylint: disable=consider-using-with
    if tls_context:
        response = urllib.request.urlopen(request, context=tls_context)
    else:
        response = urllib.request.urlopen(request)

    # - - content-type - - #
    content_type = response.getheader("Content-Type")

    if not content_type:
        response.close()
        raise ValueError("Content-Type header was not found")

    content_type = content_type.split(";")

    # check if we take the mimetype
    mimetype = content_type[0]

    if mimetype not in (
        "application/javascript",
        "application/json",
        "application/xml",
        "text/html",
        "text/javascript",
    ):
        response.close()
        raise ValueError(f'"{mimetype}" is not an accepted mimetype')

    # check if charset was specified
    try:
        charset = content_type[1].split("charset=")[1]
    except IndexError:
        charset = "utf-8"

    # - - content-length - - #
    content_length = response.getheader("Content-Length")
    max_size = 1024 * 1024 * 5

    if content_length:
        if int(content_length) > max_size:
            response.close()
            content_size = content_length / 1024 / 1024
            raise ValueError(f"file is larger than 5MB ({content_size})")

    # read data
    data = response.read(max_size + 1)
    response.close()

    if len(data) > max_size:
        raise ValueError("file is larger than 5MB")

    if len(data) == 0:
        raise ValueError("empty data returned")

    # decode data
    try:
        data = data.decode(encoding=charset)
    except:
        try:
            data = data.decode(encoding="utf-8")
        except UnicodeDecodeError:
            data = data.decode(encoding="latin-1")

    return data
