import os
from ruamel.yaml import YAML

from .default_configuration import _default_configuration


_configuration = None


def get_configuration():
    global _configuration

    if _configuration is None:
        _configuration = _load_configuration()
    return _configuration


def get_setting(name):
    return get_configuration()[name]


def _load_configuration():
    path = os.path.expanduser("~/.qt-dataviewer")
    os.makedirs(path, exist_ok=True)
    filename = os.path.join(path, "config.yaml")
    if not os.path.exists(filename):
        with open(filename, "w") as fp:
            fp.write(_default_configuration)
    _configuration = Configuration(filename)
    return _configuration


class Configuration:
    def __init__(self, filename: str | None):
        yaml = YAML()
        self.filename = filename
        if filename:
            with open(filename) as fp:
                self._config = yaml.load(fp)
        else:
            self._config = yaml.load(_default_configuration)

    def get(self, name, default=None):
        try:
            return self._get(name)
        except KeyError:
            return default

    def set(self, name, value):
        """ Changes an existing setting. """
        try:
            parts = name.split('.')
            entry = self._config
            for part in parts[:-1]:
                if entry is None:
                    raise KeyError()
                entry = entry[part]
            key = parts[-1]
            if key not in entry:
                raise KeyError()
            entry[key] = value

            self._save()

        except KeyError:
            raise KeyError(name) from None

    def add(self, name, value):
        """ Adds a new setting. """
        parts = name.split('.')
        entry = self._config
        for part in parts[:-1]:
            if part not in entry:
                entry[part] = {}
            entry = entry[part]
        key = parts[-1]
        entry[key] = value

        self._save()

    def _get(self, name, try_default=True):
        try:
            parts = name.split('.')
            value = self._config
            for part in parts:
                if value is None:
                    raise KeyError()
                value = value[part]
        except KeyError:
            if try_default:
                value = self._try_default(name)
                self.add(name, value)
            else:
                raise KeyError(name) from None
        return value

    def _try_default(self, name):
        config = Configuration(None)
        return config._get(name, try_default=False)

    def _save(self):
        yaml = YAML()
        with open(self.filename, "w") as fp:
            yaml.dump(self._config, fp)

    def __getitem__(self, name):
        return self._get(name)

    def __setitem__(self, name, value):
        self.set(name, value)
