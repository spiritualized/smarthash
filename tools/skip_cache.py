import json
import os
from json import JSONDecodeError

from termcolor import cprint

import config


class SkipCache:
    """Store skipped items in a file to avoid calling a plugin with the same data"""
    def __init__(self):
        self.disabled = False
        self.new_entries = {}
        self.existing_entries = {}
        self.load()

    def disable(self) -> None:
        self.disabled = True

    def load(self) -> None:
        if os.path.isfile(SkipCache.__cache_filename()):
            with open(SkipCache.__cache_filename(), 'r') as f:
                try:
                    serializable = json.loads(f.read())
                    self.existing_entries = {plugin: set(serializable[plugin]) for plugin in serializable.keys()}
                except JSONDecodeError:
                    cprint("Error loading skip_cache.json, file may be corrupt", 'red')

    def save(self) -> None:
        """Save out to a file. Reload existing file in case it's been overwritten by another process."""
        self.load()

        for plugin in self.new_entries:
            if plugin not in self.existing_entries:
                self.existing_entries[plugin] = set()
            self.existing_entries[plugin].update(self.new_entries[plugin])

        with open(SkipCache.__cache_filename(), 'w') as f:
            serializable = {plugin: list(self.existing_entries[plugin]) for plugin in self.existing_entries.keys()}
            f.write(json.dumps(serializable))

        self.new_entries = {}

    def add(self, plugin, path) -> None:
        if self.disabled:
            return

        if plugin not in self.new_entries:
            self.new_entries[plugin] = set()
        self.new_entries[plugin].add(path)

        # Save new entries every so often when running large bulk jobs
        if len(self.new_entries[plugin]) == 20:
            self.save()

    def in_cache(self, plugin, path) -> bool:
        if self.disabled:
            return False

        if plugin in self.existing_entries and path in self.existing_entries[plugin]:
            return True
        if plugin in self.new_entries and path in self.new_entries[plugin]:
            return True
        return False

    @staticmethod
    def __cache_filename() -> str:
        return os.path.join(os.path.dirname(os.path.abspath(config.__file__)), 'skip_cache.json')
