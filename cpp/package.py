from spack import *


class SinaCpp(CMakePackage):
    """Sina C++ Library"""

    homepage = 'https://lc.llnl.gov/confluence/display/SIBO'
    url = 'https://example.com/tarballs/dummy.tgz'

    version('develop', git='ssh://git@TODO',
            submodules=True, branch='develop')

    variant('docs', default=False,
            description='Allow generating documentation')

    # Higher versions of cmake require C++14 or newer
    depends_on('cmake@3.8.0:', type='build')
    depends_on('doxygen', type='build', when='+docs')
    depends_on('nlohmann-json -test')
