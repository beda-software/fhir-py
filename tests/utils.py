class MockAiohttpResponse:
    def __init__(self, text, status):
        self._text = text
        self.status = status

    async def text(self):
        return self._text

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


class MockRequestsResponse:
    def __init__(self, text, status_code):
        # self.json_data = json_data
        self.status_code = status_code
        self.content = text
