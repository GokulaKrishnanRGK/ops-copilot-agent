class CriticNode:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled

    def __call__(self, state: dict) -> dict:
        if not self.enabled:
            return state
        return {"critic": {"status": "noop"}}
