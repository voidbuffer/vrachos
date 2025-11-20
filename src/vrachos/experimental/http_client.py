"""Http rest api client."""

from __future__ import annotations

from typing import Any, Literal, TypeVar, overload
from urllib.parse import urljoin

import requests
from pydantic import BaseModel

from vrachos.logger import logger

_T = TypeVar("_T", bound=BaseModel)


class HttpClient:
    """Http client wrapper using Pydantic for validation."""

    def __init__(
        self,
        base_url: str,
        default_headers: dict[str, str] | None = None,
        timeout: int = 10,
    ):
        """Initialize the object."""
        self.base_url = base_url
        self.timeout = timeout
        self.default_headers = default_headers or {}
        self.session: requests.Session | None = None
        logger.debug(
            f"Initialised {self.base_url} http client"
            f" with {self.default_headers=} {timeout=}"
        )

    def __del__(self) -> None:
        """De-initialize the object."""
        logger.debug(f"De-initialised {self.base_url} http client")

    def __enter__(self) -> HttpClient:
        """Enter context manager."""
        return self

    def __exit__(
        self,
        exc_type: type | None,
        exc_value: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Exit context manager."""
        self._close()

    def _request(
        self,
        method: str,
        endpoint: str,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an http request."""
        url = urljoin(self.base_url, endpoint)
        headers = {**self.default_headers, **(override_headers or {})}

        self._ensure_session()
        if not self.session:
            raise RuntimeError("Session was not created")

        logger.debug(f"{method.upper()} {url} with {headers=} and {kwargs=}")

        try:
            response = self.session.request(
                method, url, headers=headers, timeout=self.timeout, **kwargs
            )
        except Exception as exc:
            logger.error(f"Request failed before receiving a response: {exc}")
            raise

        try:
            response.raise_for_status()
        except requests.HTTPError:
            logger.error(
                f"HTTP {response.status_code} {response.reason}"
                f" | URL={url} | Body={response.text!r}"
            )
            raise

        return response

    @overload
    def get(
        self,
        endpoint: str,
        model: type[_T],
        is_list: Literal[True],
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> list[_T]: ...

    @overload
    def get(
        self,
        endpoint: str,
        model: type[_T],
        is_list: Literal[False] = False,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _T: ...

    def get(
        self,
        endpoint: str,
        model: type[_T],
        is_list: bool = False,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _T | list[_T]:
        """GET request returning a typed model or list of typed models."""
        response = self._request("GET", endpoint, override_headers, **kwargs)
        data = response.json()

        if is_list:
            if not isinstance(data, list):
                raise ValueError(
                    f"Expected list but got {type(data).__name__}"
                )
            return [model.model_validate(item) for item in data]
        else:
            if isinstance(data, list):
                raise ValueError("Expected object but got list")
            return model.model_validate(data)

    def post(
        self,
        endpoint: str,
        model: type[_T],
        data: BaseModel | dict[str, Any] | None = None,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _T:
        """POST request returning a typed model."""
        if isinstance(data, BaseModel):
            kwargs["json"] = data.model_dump()
        elif data is not None:
            kwargs["json"] = data

        response = self._request("POST", endpoint, override_headers, **kwargs)
        return model.model_validate(response.json())

    def patch(
        self,
        endpoint: str,
        model: type[_T],
        data: BaseModel | dict[str, Any] | None = None,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _T:
        """PATCH request returning a typed model."""
        if isinstance(data, BaseModel):
            kwargs["json"] = data.model_dump()
        elif data is not None:
            kwargs["json"] = data

        response = self._request("PATCH", endpoint, override_headers, **kwargs)
        return model.model_validate(response.json())

    def update(
        self,
        endpoint: str,
        model: type[_T],
        data: BaseModel | dict[str, Any] | None = None,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> _T:
        """PUT request returning a typed model."""
        if isinstance(data, BaseModel):
            kwargs["json"] = data.model_dump()
        elif data is not None:
            kwargs["json"] = data

        response = self._request("PUT", endpoint, override_headers, **kwargs)
        return model.model_validate(response.json())

    def delete(
        self,
        endpoint: str,
        override_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """DELETE request returning response data."""
        response = self._request(
            "DELETE", endpoint, override_headers, **kwargs
        )

        # Handle empty responses
        if response.text:
            data: dict[str, Any] = response.json()
            return data
        return {"status": "deleted"}

    def _ensure_session(self) -> None:
        """Ensure there is a session."""
        if not self.session:
            self.session = requests.Session()
            logger.debug(f"New session of {self.base_url} http client")

    def _close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            self.session = None
            logger.debug(f"Closed session of {self.base_url} http client")


if __name__ == "__main__":
    # Example: Using with JSONPlaceholder API
    class Post(BaseModel):
        """Example Pydantic model."""

        userId: int
        id: int
        title: str
        body: str

    class User(BaseModel):
        """Example Pydantic model."""

        id: int
        name: str
        email: str
        username: str

    client: HttpClient = HttpClient(
        base_url="https://jsonplaceholder.typicode.com"
    )

    # GET single resource
    post = client.get("posts/1", model=Post)
    print(f"Post: {post.title}")

    # GET list of resources
    posts = client.get("posts", model=Post, is_list=True, params={"_limit": 5})
    print(f"First 5 posts: {len(posts)}")
    for post in posts:
        print(f"Title: {post.title}")

    # GET user
    user: User = client.get("users/1", User)
    print(f"User: {user.name} ({user.email})")
