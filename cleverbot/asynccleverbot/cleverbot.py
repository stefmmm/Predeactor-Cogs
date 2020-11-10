"""
MIT License

Copyright (c) 2018-2020 crrapi                                                (Note: User deleted)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from enum import Enum

import aiohttp


class Emotion(Enum):
    """Enum used to pass an emotion to the API."""

    neutral = "neutral"
    normal = "neutral"
    sad = "sadness"
    sadness = "sadness"
    fear = "fear"
    scared = "fear"
    joy = "joy"
    happy = "joy"
    anger = "anger"
    angry = "anger"


class APIDown(Exception):
    """API is down."""


class InvalidKey(Exception):
    """API key invalid."""


class DictContext:
    """Context for API requests."""

    def __init__(self):
        self._storage = dict()

    def update_context(self, id_, query):
        """Pushes data to the Context."""
        try:
            ctx = self._storage[id_]
        except KeyError:
            li_temp = list()
            li_temp.append(query)
            self._storage[id_] = li_temp
            return dict(text=query)
        else:
            self._storage[id_].append(query)
            if len(self._storage[id_]) > 2:
                self._storage[id_].pop(0)
                return dict(text=query, context=ctx)
        return dict(text=query)


class Response:
    """
    Represents a response from a successful bot query.
    You do not make these on your own, you usually get them from `ask()`.
    """

    def __init__(self, text, status):
        self.text = text
        self.status = status

    def __str__(self):
        return self.text

    @classmethod
    def from_raw(cls, data):
        """Creates a Response from raw data"""
        try:
            return cls(data["response"], data["status"])
        except KeyError:
            raise APIDown("The API did not return a response.")


class Cleverbot:
    """The client to use for API interactions."""

    def __init__(
        self, api_key: str, session: aiohttp.ClientSession = None, context: DictContext = None
    ):
        self.context = context or None
        self.session = session or None
        self.api_key = api_key  # API key for the Cleverbot API
        self.api_url = "https://public-api.travitia.xyz/talk"  # URL for requests
        if session and not isinstance(session, aiohttp.ClientSession):
            raise TypeError("Session must be an aiohttp.ClientSession.")
        if context:
            self.set_context(context)

    def set_context(self, context: DictContext):
        """Sets the Cleverbot's context to an instance of DictContext."""
        if not isinstance(context, DictContext):
            raise TypeError("Context passed was not an instance of DictContext.")
        else:
            self.context = context

    async def ask(self, query: str, id_=None, *, emotion: Emotion = Emotion.neutral):
        """Queries the Cleverbot API."""
        if not self.session:
            self.session = aiohttp.ClientSession()  # Session for requests
        if not isinstance(emotion, Emotion):
            raise ValueError("emotion must be an enum of async_cleverbot.Emotion.")
        if isinstance(self.context, DictContext):
            ctx = self.context.update_context(id_, query)
        else:
            ctx = dict(text=query)
        ctx["emotion"] = emotion.value
        headers = dict(authorization=self.api_key)
        async with self.session.post(self.api_url, data=ctx, headers=headers) as req:
            try:
                resp = await req.json()
            except aiohttp.ContentTypeError:
                raise APIDown(
                    "The API is currently not working. Please wait while the devs fix it."
                )

            if resp.get("error") == "Invalid authorization credentials":
                raise InvalidKey("The API key you provided was invalid.")

            if resp.get("response") == "The server returned a malformed response or it is down.":
                raise APIDown(
                    "The API is currently not working. Please wait while the devs fix it."
                )

        return Response.from_raw(resp)

    async def close(self):
        """Closes the aiohttp session."""
        if self.session:
            await self.session.close()
