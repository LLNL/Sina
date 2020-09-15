from spack import *


class SinaCpp(CMakePackage):
    """Sina C++ Library"""

    homepage = 'https://lc.llnl.gov/confluence/display/SIBO'
    url = 'https://example.com/tarballs/dummy.tgz'

    version('develop', git='ssh://git@TODO',
            submodules=True, branch='develop')

    variant('docs', default=False,
            description='Allow generating documentation')
    variant('adiak', default=False,
            description='Create interface for calling Sina through Adiak')
    variant('test', default=True,
            description='Build tests')

    # Higher versions of cmake require C++14 or newer
    depends_on('cmake@3.8.0:', type='build')
    depends_on('adiak', when='+adiak')
    depends_on('doxygen', type='build', when='+docs')
    depends_on('conduit ~python ~mpi ~hdf5 ~silo ~shared ~test ~hdf5_compat')

    def configure_args(self):
        spec = self.spec if self.spec is not None else ""
        return [
            '-DSINA_BUILD_ADIAK_BINDINGS={0}'.format('YES' if '+adiak' in spec else 'NO'),
            '-DSINA_BUILD_TESTS={0}'.format('NO' if '-test' in spec else 'YES'),
        ]
