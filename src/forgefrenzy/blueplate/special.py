""" 
blueplate.special: a blueprint for sensible command line tools
"""

import os
import sys
import argparse
import inspect

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from .imports import minimock, mock, doctest
from .version import version
from .logger import log


class Special:
    """blueplate.special: a blueprint for sensible command line tools"""

    default_level = log.config.default
    options = []
    errors = {}
    testmode = False

    def __init__(self, argv=None):
        """
        >>> Special().argv == sys.argv[1:]
        True
        >>> Special("--debug").argv == ["--debug"]
        True
        >>> Special("--debug --log").argv == ["--debug", "--log"]
        True
        >>> Special(["--debug", "--log --debugv"]).argv
        ['--debug', '--log', '--debugv']
        """
        self.__module = sys.modules[self.__class__.__module__]
        self.__version = self.__module.version
        self.description = self.__doc__.splitlines()[0].strip()
        if ":" in self.description:
            self.name, self.description = self.description.split(":", 1)
            self.name = self.name.strip()
            self.description = self.description.strip()
        else:
            self.name = self.__class__.__name__

        log.critical(f"Creating object with args {argv=}")
        if argv is not None:
            if isinstance(argv, str):
                log.debug(
                    f"Creating {self.__class__.__name__} object using provided string {argv=}"
                )
                self.argv = argv.split(" ")
            elif isinstance(argv, list):
                log.debug(f"Creating {self.__class__.__name__} object using provided list {argv=}")
                self.argv = argv
            else:
                log.warning(
                    "Provided value for argv is neither a string nor list, continuing without args"
                )
                self.argv = []
        else:
            log.debug(f"Creating {self.__class__.__name__} object using {sys.argv[1:]=}")
            self.argv = sys.argv[1:]

        # Remove empty strings
        self.argv = [arg for subarg in self.argv for arg in subarg.split(" ") if arg]

        self.__options = None
        self.__args = None
        self.__argparser = None
        self.__errors = None

    def main(self):
        """Stub main
        >>> sys.argv = "special.py --log".split()
        >>> special = Special("")
        >>> mock("special.help")
        >>> special.main()
        Called special.help()
        """
        log.config.update(self)

        if self.args.test:
            self.test()
            return

        if self.args.version:
            print(self.version)
            return

        self.fn()

    @property
    def version(self):
        return self.__version

    def fn(self):
        self.help()

    def help(self):
        """Show usage text
        # >>> special.argv
        >>> special.help()
        usage: ...
        ...
        options:
        ...
        arguments:
        ...
        error codes:
        ...
        """
        print(
            f"""\
{self.show_usage()}
{self.show_args()}

{self.show_errors()}
"""
        )

    @property
    def argparser(self):
        """Generate an arg parser object with all the args from the caller and the util module
        >>> special.argparser
        ArgumentParser(...
        >>> special.argparser.description == special.description
        True
        """
        if self.__argparser is not None:
            return self.__argparser

        self.__argparser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        # Add all arguments to the parser
        for option in self.options:
            option = option.copy()
            args = option.pop("args")
            kwargs = option
            self.__argparser.add_argument(*args, **kwargs)

        return self.__argparser

    @property
    def args(self):
        """Get the args, handle default args
        # >>> print(Special("--debug").show_args())
        >>> Special("--debug").args.debug
        True
        >>> Special("--debug").args.test
        False
        """
        if self.__args is not None:
            return self.__args

        try:
            self.__args = self.argparser.parse_args(self.argv)
        except Exception as ex:
            self.error("bad-args", e=ex)

        return self.__args

    def show_usage(self):
        return self.argparser.format_help()

    def show_args(self):
        """Display a list of all arguments parsed
        >>> print(Special("--log --debugv").show_args())
        arguments:
          log               True
          console           False
          debug             False
          debugv            True
          test              False
          version           False
        """
        output = ["arguments:"]

        for arg, val in vars(self.args).items():
            output.append(f"  {arg:17} {val}")

        return "\n".join(output)

    def show_errors(self):
        """Render a table of error messages and exit codes
        >>> print(special.show_errors())
        error codes:
          128               The error key {key} is undefined.
        ...
        """
        output = ["error codes:"]

        for error, index in self.errors.values():
            output.append(f"  {index:<17} {error}")

        return "\n".join(output)

    @property
    def config(self):
        defaults_file = os.path.join(os.path.dirname(__file__), "defaults.toml")
        config_file = os.path.join(
            os.path.dirname(self.__module.__file__), "..", "..", "pyproject.toml"
        )

        with open(defaults_file, "rb") as f:
            defaults = tomllib.load(f).get("tools", {}).get("blueplate", {})

        try:
            with open(config_file, "rb") as f:
                config = tomllib.load(f).get("tools", {}).get("blueplate", {})
        except FileNotFoundError:
            log.warning(f"Could not find package configuration TOML: {config_file}")
            config = {}

        return {
            "options": defaults.get("options", {}) | config.get("options", {}),
            "errors": defaults.get("errors", {}) | config.get("errors", {}),
        }

    @property
    def options(self):
        if self.__options is not None:
            return self.__options

        self.__options = []

        for arg, details in self.config["options"].items():
            details["args"] = [f"--{arg}"] + details.pop("alternates", [])
            self.__options.append(details)

        return self.__options

    @property
    def errors(self):
        """
        >>> special.errors["bad-args"]
        ('Arguments provided were invalid: {e}', 129)
        >>> special.errors["test-error"]
        ('DocTest exectution failed due to exception during execution', 131)
        """
        if self.__errors is not None:
            return self.__errors

        self.__errors = {}

        for error, message in self.config["errors"].items():
            error_code = list(self.config["errors"].keys()).index(error) + 128
            self.__errors[error] = (message, error_code)

        return self.__errors

    def error(self, key, **kwargs):
        """Format the error string, raise an exception or log the error and exit with the error code
        >>> special.error("not-a-real-error")
        Traceback (most recent call last):
        SystemExit: 128
        >>> special.error("unknown-error", key="missing-key")
        Traceback (most recent call last):
        ...
        TypeError: ...error() got multiple values for argument 'key'
        >>> special.error("test-failure")
        Traceback (most recent call last):
        SystemExit: 130
        >>> special.error("test-error")
        Traceback (most recent call last):
        SystemExit: 131
        """
        if key not in self.errors.keys():
            # If not defined, use catchall
            kwargs["key"] = key
            key = "unknown-error"

        string, code = self.errors[key]
        formatted_string = string.format(**kwargs)

        log.critical(f"Exit {code}: {formatted_string}")
        print(f"Exit {code}: {formatted_string}")

        exit(code)

    def test_globs(self):
        """Define test tools for Doctest
        >>> list(special.test_globs().keys())
        ['mock', 'minimock', 'special']
        """
        from .imports import minimock, mock

        globs = {"mock": mock, "minimock": minimock, "special": type(self)("")}
        return globs

    def test(self, mock_test=False):
        """Run Doctests
        >>> special.test(mock_test=True)
        Called doctest.testmod(
            <module '...' from '.../special.py'>,
        ...
        """
        module = sys.modules[self.__class__.__module__]

        result = test_module(module, self.test_globs(), mock_test)

        if result is not None:
            self.error(result)


def test_module(module, test_globs=None, mock_test=False):
    """Run Doctests
    >>> test_module(sys.modules[special.__module__], mock_test=True)
    Called doctest.testmod(
        <module '...' from '.../special.py'>,
    ...
    """

    filename = os.path.basename(module.__file__)
    testmod = doctest.testmod

    if mock_test:
        doctest.testmod = minimock.Mock("doctest.testmod")
        log.alert(f"Simulating doctests of module {module} in file {filename} with mock")
        log.debugv(f"{doctest.testmod=}")
    else:
        log.alert(f"Running doctests of module {module} in file {filename}")
        log.debugv(f"{doctest.testmod=}")

    try:
        log.critical(f"{module=}")
        doctest.testmod(
            module,
            raise_on_error=True,
            verbose=True,
            extraglobs=test_globs,
            optionflags=doctest.ELLIPSIS,
        )
    except doctest.DocTestFailure as e:
        log.critical(f"doctest failed: DocTestFailure")
        log.config.console = True
        log.config.level = "ERROR"
        try:
            e_path = f"{os.path.basename(e.test.filename)}:{(e.test.lineno + e.example.lineno + 1)}"
        except:
            e_path = "Unknown"

        e_str = f"""
=======================================
    DocTestFailure
        {e.test.name}
        {e_path}
=======================================
        
    Trying:
        {e.example.source}
    Expected:
        {e.example.want.strip() or "-----"}
        
    Got:
        {e.got}

=======================================
"""
        log.error(e_str)
        return "test-failure"
    except doctest.UnexpectedException as e:
        log.critical(f"doctest failed: UnexpectedException")
        log.config.console = True
        log.config.level = "ERROR"
        try:
            e_path1 = (
                f"{os.path.basename(e.test.filename)}:{(e.test.lineno + e.example.lineno + 1)}"
            )
        except:
            e_path1 = "Unknown"
        try:
            e_path2 = f"...{os.path.dirname(e.exc_info[2].tb_next.tb_next.tb_frame.f_code.co_filename)[-15:]}/{os.path.basename(e.exc_info[2].tb_next.tb_next.tb_frame.f_code.co_filename)}:{e.exc_info[2].tb_next.tb_next.tb_frame.f_lineno} in '{e.exc_info[2].tb_next.tb_next.tb_frame.f_code.co_name}'"
        except:
            e_path2 = "Unknown"
        e_str = f"""
=======================================
    UnexpectedException
        {e.test.name}
        {e_path1}
=======================================
        
    Trying:
        {e.example.source}
    Expected:
        {e.example.want.strip() or "-----"}
        
    Exception:
        {e.exc_info[0].__name__}: {e.exc_info[1]}
        {e_path2}

=======================================

"""
        log.exception(e_str)
        return "test-error"
    finally:
        doctest.testmod = testmod


def get_caller_module(level=None, ignore_direct_caller=True, ignore_self=True):
    """Return the module which called this function
    ignore_direct_caller    Starts at the caller of the caller
    ignore_self             Ignore all this of this module
    """
    ignore_modules = []

    if ignore_self:
        ignore_modules.append(sys.modules[__name__])

    frame = inspect.currentframe()

    from pprint import pprint

    # pprint(frame)
    # print(dir(frame))
    index = 0
    stack = []
    while frame.f_back is not None:
        # print(f"#{index} {frame=}")
        stack.append(frame)
        index += 1
        frame = frame.f_back

        if level is not None and level >= index:
            break

    for k, v in sys.modules.items():
        if v == k:
            return sys.modules[k]

    print(dir(frame))
    # help(frame)
    print({k: getattr(frame, k) for k in dir(frame)})
    # pprint(sys.modules)

    if __name__ == "__main__":
        module_obj = sys.modules[__name__]
    else:
        module_name = inspect.getmodulename(inspect.stack()[0][1])
        log.debug(f"Found root module '{module_name}'")
        module_obj = sys.modules[module_name]

        # print(f"{__name__=}")
        module_obj = sys.modules["__main__"]
        # print(f"{module_obj=}")
        pprint({k: getattr(module_obj, k) for k in dir(module_obj)})
    return module_obj


if __name__ == "__main__":
    script = Special()
    script.main()
