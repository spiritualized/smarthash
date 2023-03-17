import builtins


class MockFile:
    class MockFileInstance:
        def __init__(self):
            self.data = []

        def write(self, data):
            self.data = data

        def __enter__(self):
            return self

        def __exit__(self, _type, _value, _traceback):
            pass

    builtin_open = open
    mock_data = {}

    @staticmethod
    def register_path(path) -> None:
        MockFile.mock_data[path] = MockFile.MockFileInstance()

    @staticmethod
    def reset() -> None:
        for item in MockFile.mock_data.values():
            del item
        MockFile.mock_data = {}

    @staticmethod
    def open(*args, **kwargs):
        if args[0] in MockFile.mock_data:
            return MockFile.mock_data[args[0]]
        return MockFile.builtin_open(*args, **kwargs)

    @staticmethod
    def get_data(path):
        if path not in MockFile.mock_data.keys():
            raise ValueError(f"Unregistered path: {path}")
        return MockFile.mock_data[path].data

    def __init__(self, param):
        if type(param) == list:
            for path in param:
                MockFile.register_path(path)
        else:
            MockFile.register_path(param)

        builtins.open = MockFile.open

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        MockFile.reset()
        builtins.open = MockFile.builtin_open
