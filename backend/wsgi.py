from urllib.parse import parse_qs

from backend.app import ApiApp


STATUS_TEXT = {
    200: "OK",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    500: "Internal Server Error",
}


def _headers_from_environ(environ) -> dict[str, str]:
    headers = {}
    for key, value in environ.items():
        if key.startswith("HTTP_"):
            header_name = key.removeprefix("HTTP_").replace("_", "-").title()
            headers[header_name] = value
    if "CONTENT_TYPE" in environ:
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    return headers


def _query_from_environ(environ) -> dict[str, str]:
    parsed = parse_qs(environ.get("QUERY_STRING", ""), keep_blank_values=True)
    return {key: values[-1] for key, values in parsed.items()}


def make_wsgi_app(api_app: ApiApp):
    def application(environ, start_response):
        response = api_app.handle_request(
            method=environ.get("REQUEST_METHOD", "GET"),
            path=environ.get("PATH_INFO", "/"),
            headers=_headers_from_environ(environ),
            query=_query_from_environ(environ),
        )
        status_line = f"{response.status_code} {STATUS_TEXT.get(response.status_code, 'Unknown')}"
        body = response.body.encode("utf-8")
        headers = list(response.headers.items())
        headers.append(("Content-Length", str(len(body))))
        start_response(status_line, headers)
        return [body]

    return application
