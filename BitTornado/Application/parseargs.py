def formatDefinitions(options, COLS, presets={}):
    """Format command-line options and documentation to fit into a given
    column width

    Parameters
        tuple[] - (flag, default, docstring) tuples describing each flag
        int     - Number of columns to write
        dict    - {flag: value} overrides for default values (default: {})

    Return
        str     - Printable output
    """

    # Number of spaces before each line
    # Default to 10, but reduce to 1 if this results in very low width
    spaces = " " * 10
    width = COLS - 11
    if width < 15:
        width = COLS - 2
        spaces = " "

    lines = []
    # Display flag name, followed by indented documentation string
    for (longname, default, doc) in options:
        lines.append("--{} <arg>".format(longname))
        default = presets.get(longname, default)

        # Don't add default info for empty strings or None
        if default not in ('', None):
            doc += ' (defaults to {})'.format(default)

        # Word wrap documentation string
        while len(doc) > width:
            pre, _, post = doc[:width].rpartition(' ')
            doc = post + doc[width:]
            lines.append(spaces + pre)
        if doc:
            lines.append(spaces + doc)

        lines.append('')
    return '\n'.join(lines)


def defaultargs(options):
    """Produce a dictionary of default arguments from a list of options
    tuples

    Parameter
        tuple[] - (flag, default, docstring) tuples describing each flag

    Return
        dict    - {flag: default} for each option in input
    """
    config = {}
    for longname, default, _ in options:
        config[longname] = default
    return config


def parseargs(argv, options, minargs=0, maxargs=None, presets={}):
    """Parse an argument list, given a list of options, with defaults,

    Parameter
        str[]   - Indexable sequence of arguments (list or tuple)
        tuple[] - (flag, default, docstring) tuples describing each flag
        int     - Minimum number of non-option arguments
        int     - Maximum number of non-option arguments (no max if None)
        dict    - {flag: value} overrides for default values (default: {})

    Return
        dict    - {flag: value} for each option in input
        str[]   - List of non-option arguments found in argv
    """
    # This is faster than dict comprehensions
    config = {}
    for longname, default, _ in options:
        config[longname] = default

    # presets after defaults but before arguments
    config.update(presets)

    args = []
    while argv:
        arg, argv = argv[0], argv[1:]

        # Non-option
        if arg[:2] != '--':
            args.append(arg)
            continue

        if not argv:
            raise ValueError('parameter passed in at end with no value')
        # Get flag/value
        key, value, argv = arg[2:], argv[0], argv[1:]

        if key not in config:
            raise ValueError('unknown key --' + key)

        # Coerce value type to the type of default arg
        try:
            if config[key] is None or isinstance(config[key], str):
                config[key] = value
            elif isinstance(config[key], int):
                config[key] = int(value)
            elif isinstance(config[key], float):
                config[key] = float(value)
            else:
                assert 0
        except ValueError as e:
            raise ValueError('wrong format of --%s - %s' % (key, str(e)))

    # Non-optional flags are denoted by a None default argument
    for key, value in config.items():
        if value is None:
            raise ValueError("Option --%s is required." % key)

    # Check number of arguments
    if len(args) < minargs:
        raise ValueError("Must supply at least %d args." % minargs)
    if maxargs is not None and len(args) > maxargs:
        raise ValueError("Too many args - %d max." % maxargs)

    return (config, args)
