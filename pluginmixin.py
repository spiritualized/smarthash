
class PluginArgument:

    def __init__(self, argument: str, **kwargs):
        self.argument = argument
        self.kwargs = kwargs


class PluginMixin:

    def __init__(self):
        self.arguments = []

    def add_argument(self, argument: str, **kwargs):
        self.arguments.append(PluginArgument(argument, **kwargs))
