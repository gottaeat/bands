class BandsAI:
    _MODEL = "gpt-5-nano"
    _TOKEN_LIMIT = 400

    def __init__(self, parent_logger, client):
        self.logger = parent_logger.getChild(self.__class__.__name__)

        self.responses = client.responses

    def query(self, system_prompt, user_prompt):
        try:
            response = self.responses.create(
                model=self._MODEL,
                instructions=system_prompt,
                input=user_prompt,
                max_output_tokens=self._TOKEN_LIMIT,
                tools=[],
                reasoning={"effort": "minimal"},
            )
        except:
            self.logger.exception("openai query failed")

        return response.output_text.strip()
