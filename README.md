# nopkg 

Install your custom python modules into any python environment without setup.py, pyproject.toml, or any other typical python packaging setup. 

Use For:

- Personal scripts and utilities 
- Prototyping, evaluating the usefulness of a module before putting the effort into packaging
- Sharing small utilities with your team, without maintaining a proper pip package or hosting an internal pip repository

## Install python files as importable (from anywhere) modules

Install your module with `nopkg`

```sh
nopkg install mymodule.py 
```

Use it in python

```py
from mymodule import hello

hello("I just installed a module without any setup!")
```

## Works with venv (of course)

```sh
# Create and activate virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install your module
nopkg install mymodule.py

# Use it in your virtual environment
python -c "from mymodule import hello; hello('Virtual env works!')"
```

## Editable installs 

Install your python file(s) as an importable module, and keep them exactly where they are. Changes to
your files will take effect immediately without any re-installing.

```sh
nopkg install -e mymodule.py
```

## Install from URL

No need to limit yourself to python modules you have locally, `nopkg` will happily download and
install modules from a URL as well!

```sh
nopkg install https://raw.githubusercontent.com/user/repo/main/utils.py
```


## Managing Installed Modules

### Ensure the expected interpreter is being used

```sh
nopkg env current
```

`nopkg` should be reasonably smart about selecting the correct interpreter, but if you ever need to tell it explicitly 

```sh
nopkg env use /path/to/my/python
```

Most commands also accept a `--python` CLI option to use a specific interpreter for that command

```
nopkg install mymodule --python /path/to/my/python
```

### List installed modules
```sh
nopkg ls
```

### Remove an installed module
```sh
nopkg uninstall mymodule
```

## Real-world Examples

## Installation

```sh
pip install nopkg
```

## How it works

`nopkg` installs packages directly into python's site-packages directory. It doesn't do all of the things
that pip does, it's much more simple. Either:

- a) a `.pth` file gets added to site-packages, which tells python the location (absolute path) of your module. This is essenially the same as appending to `sys.path`, but is applied automatically. This is how ediable installs in pip work as well
- b) your source files are copied directly into site-packages as-is. Roughly equivelent to a source install with pip

In order to make sure you don't leave your site-packages in a bad state, `nopkg` keeps a simple registry file to track what is insalled where. This drives the `nopkg ls` command as well as enabling `nopkg uninstall`. 

All this means:

- No `setup.py` required
- No `pyproject.toml` needed
- No wheel building

But also means:

- You can't publish to PyPI (still need setup.py or pyproject.toml for that)
- You can't use C extensions or other native bindings
   - `nodtl` will copy **ALL** the files into site-packages when you give a directory -- so there is a chance this might actually work, but it isn't a supported use case
- Inter-module dependencies can be a mess

`nopkg` is intended as a tool for personal utility management and prototyping, as well as sharing of ad-hoc utility modules within a team. `nopkg` is NOT intended as a pip replacement or production package management solution. It is a bridge that lets you get going quickly.

## Things `nopkg` might do in the future! (Contributions Welcome)

- `nopkg pipify mymodule.py`: Setup the boilerplate for full python packaging and pypi publishing


## License

MIT

