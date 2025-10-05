# nopkg 

Install your custom python modules into any python environment without setup.py, pyproject.toml, or any other typical python packaging setup. 

Use For:

- Personal scripts and utilities 
- Prototyping, evaluating the usefulness of a module before putting the effort into packaging
- Sharing small utilities with your team, without maintaining a proper pip package or hosting an internal pip repository

## Install python files as importable modules

Install a single Python file as a module:

```sh
nopkg install mymodule.py 
```

Install a directory as a package (will create `__init__.py` if needed):

```sh
nopkg install mypackage/
```

Use it in python:

```py
from mymodule import hello
from mypackage import utils

hello("I just installed a module without any setup!")
```

## Works with virtual environments

```sh
# Create and activate virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install your module
nopkg install mymodule.py

# Use it in your virtual environment
python -c "from mymodule import hello; hello('Virtual env works!')"
```

## Development mode installs 

Install your python file(s) as an importable module, and keep them exactly where they are. Changes to
your files will take effect immediately without any re-installing.

```sh
nopkg install -e mymodule.py
nopkg install --dev mypackage/
```


## Managing Installed Modules

### List installed modules
```sh
nopkg list
```

### Show module information
```sh
nopkg info mymodule
```

### Update an installed module
```sh
nopkg update mymodule
```

### Remove an installed module
```sh
nopkg uninstall mymodule
```

## Installation

```sh
pip install nopkg
```

## How it works

`nopkg` installs modules and packages directly into Python's site-packages directory. It's much simpler than pip and works in one of two ways:

- **Development mode (`-e` or `--dev`)**: Creates a `.pth` file in site-packages that points to your module's location. Changes to your files are immediately available without reinstalling.
- **Copy mode (default)**: Copies your source files directly into site-packages.

`nopkg` maintains a simple registry file (`~/.nopkg/registry.txt`) to track installations, enabling the `list`, `info`, `update`, and `uninstall` commands.

All this means:

- No `setup.py` required
- No `pyproject.toml` needed
- No wheel building

**Limitations:**

- Cannot publish to PyPI (still need setup.py or pyproject.toml for that)
- No dependency management - you must manually ensure dependencies are installed
- Only works with local files and directories (no URL installation)
- Package directories are copied entirely, preserving all resource files and assets

`nopkg` is intended as a tool for personal utility management and prototyping, as well as sharing of ad-hoc utility modules within a team. `nopkg` is NOT intended as a pip replacement or production package management solution. It is a bridge that lets you get going quickly.

## Available Commands

```
nopkg install <source>     # Install a module or package
nopkg install -e <source>  # Install in development mode  
nopkg list                 # List installed modules
nopkg info <module>        # Show module information
nopkg update <module>      # Update an installed module
nopkg uninstall <module>   # Remove an installed module
```

**Note**: The core functionality supports specifying different Python interpreters, but the CLI doesn't expose this feature yet.

## Future Features (Contributions Welcome!)

- **URL Installation**: `nopkg install https://raw.githubusercontent.com/user/repo/main/utils.py`
- **CLI Python Interpreter Selection**: `nopkg install mymodule --python /path/to/python`
- **Environment Management**: `nopkg env current`, `nopkg env use /path/to/python`
- **Package Bootstrapping**: `nopkg pipify mymodule.py` - Setup boilerplate for full Python packaging and PyPI publishing
- **Dependency Detection**: Automatically detect and warn about missing dependencies

## License

MIT

