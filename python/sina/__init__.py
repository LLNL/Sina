"""Logic for handling inserting, extracting, and transforming data between backends."""

# Note that the C++ spack package builder references this version string
__VERSION__ = "1.8.0"


def get_version():
    """Get the version of the package."""
    return __VERSION__
