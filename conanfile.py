import os, sys, shutil, re
from conans import ConanFile, CMake, tools
from conans.errors import ConanException


class MrptConan(ConanFile):
    name = "mrpt"
    version = "1.5.5"
    license = "BSD"
    url = "http://www.mrpt.org/"
    description = "<Description of Mrpt here>"
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    requires = (
        'eigen/[>=3.2.0]@ntc/stable',
        'vtk/[>=5.6.1]@3dri/stable',
        'freeglut/[>=3.0.0]@3dri/stable',
        'opencv/[>=3.1.0]@3dri/stable',
        'assimp/[>=3.1]@3dri/stable',
        'zlib/[>=1.2.11]@conan/stable',
        'pcl/[>=1.7.0]@3dri/stable',
    )
    options = {"shared": [True, False]}
    default_options = "shared=True"

    def configure(self):
        self.options['opencv'].shared = self.options.shared
        self.options['zlib'].shared = self.options.shared

    def source(self):

        ext = "tar.gz" if self.settings.os == "Linux" else "zip"
        archive=f'{self.version}.{ext}'
        archive_url=f'https://github.com/MRPT/mrpt/archive/{archive}'

        hashes = {
            '1.5.5.tar.gz': '3f74fecfe1a113c350332122553e1685',
            '1.5.5.zip':    '48c188d70a3844ab49036a05cf5786fd',
            '1.4.0.tar.gz': 'ca36688b2512a21dac27aadca34153ce',
            '1.4.0.zip':    'db58a092e984aeb95666477339b832f0',
        }

        tools.download(url=archive_url, filename=archive)
        try:
            tools.check_md5(archive, hashes[archive])
        except ConanException as e:
            self.output.error(e)
            sys.exit(-1)

        tools.unzip(archive)
        shutil.move(f'mrpt-{self.version}', self.name)

    def system_requirements(self):
        pack_names = None
        if tools.os_info.linux_distro == "ubuntu":
            # Minimal requirements
            # (removed from here because we provide our own: libopencv-dev,
            # libeigen3-dev, libgtest-dev)
            pack_names = [
                'build-essential', 'pkg-config', 'cmake', 'libwxgtk3.0-dev'
            ]

            # Additional
            # (removed from here because we provide our own: zlib1g-dev
            # libassimp-dev, freeglut3-dev)  Also, removed liboctomap-dev
            # because it doesn't seem to exists.
            pack_names = [
                'libftdi-dev', 'libusb-1.0-0-dev', 'libudev-dev',
                'libfreenect-dev', 'libdc1394-22-dev', 'libavformat-dev',
                'libswscale-dev', 'libjpeg-dev', 'libsuitesparse-dev',
                'libpcap-dev',
            ]

            if self.settings.arch == "x86":
                full_pack_names = []
                for pack_name in pack_names:
                    full_pack_names += [pack_name + ":i386"]
                pack_names = full_pack_names

        if pack_names:
            installer = tools.SystemPackageTool()
            installer.update() # Update the package database
            installer.install(" ".join(pack_names)) # Install the package

    def build(self):

        vtk_major    = '.'.join(self.deps_cpp_info['vtk'].version.split('.')[:2])
        pcl_major    = '.'.join(self.deps_cpp_info['pcl'].version.split('.')[:2])

        args = []

        if self.options.shared:
            args.append('-DBUILD_SHARED_LIBS:BOOL=TRUE')
        args.append('-DBUILD_EXAMPLES:BOOL=FALSE')
        args.append('-DMRPT_HAS_ASIAN_FONTS:BOOL=FALSE')
        args.append('-DCMAKE_CXX_FLAGS="-fPIC"')
        args.append('-DOpenCV_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['opencv'].rootpath, 'share', 'OpenCV'))
        args.append('-DPCL_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['pcl'].rootpath, 'share', f'pcl-{pcl_major}'))
        args.append('-DVTK_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['vtk'].rootpath, 'lib', 'cmake', f'vtk-{vtk_major}'))
        args.append('-DGLUT_INCLUDE_DIR=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'include'))
        args.append('-DGLUT_glut_LIBRARY=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'lib', 'libglut.so'))

        args.append('-DZLIB_INCLUDE_DIR=%s'%os.path.join(self.deps_cpp_info['zlib'].rootpath, 'include'))
        if self.options.shared:
            libz = 'libz.so' if self.settings.os == 'Linux' else 'libz.dll'
        else:
            libz = 'libz.a' if self.settings.os == 'Linux' else 'libz.lib'
        args.append('-DZLIB_LIBRARY_RELEASE=%s'%os.path.join(self.deps_cpp_info['zlib'].rootpath, 'lib', libz))

        args.append('-DBUILD_ASSIMP:BOOL=FALSE')
        pkg_vars = {
            'PKG_CONFIG_eigen3_PREFIX':  self.deps_cpp_info['eigen'].rootpath,
            'PKG_CONFIG_assimp_PREFIX': self.deps_cpp_info['assimp'].rootpath,
            'PKG_CONFIG_pcl_PREFIX':    self.deps_cpp_info['pcl'].rootpath,
            'PKG_CONFIG_PATH': ':'.join([
                os.path.join(self.deps_cpp_info['eigen'].rootpath, 'share', 'pkgconfig'),
                os.path.join(self.deps_cpp_info['assimp'].rootpath, 'lib', 'pkgconfig'),
                os.path.join(self.deps_cpp_info['pcl'].rootpath, 'lib', 'pkgconfig'),
            ])
        }

        cmake = CMake(self)
        with tools.environment_append(pkg_vars):
            cmake.configure(source_folder=self.name, args=args)
            cmake.build()

        # Fix up the CMake Find Script MRPT generated
        self.output.info('Inserting Conan variables in to the PCL CMake Find script.')

        cmake.install()

        self.fixFindPackage(os.path.join(self.package_folder, 'share', 'mrpt', 'MRPTConfig.cmake'))


    def fixFindPackage(self, path):
        """
        Insert some variables into the MRPT find script generated in the
        build so that we can use it in our CMake scripts
        """

        if not os.path.exists(path):
            self.output.warn('Could not fix non-existant file: %s'%path)
            return

        with open(path) as f:
            data = f.read()

        m = re.search(r'SET.MRPT_DIR "(?P<base>.*?)(?P<type>(build|package))(?P<rest>.*?(?="))', data)
        if not m:
            self.output.warn('Could not find MRPT source directory in CMake file')
            return
        for t in ['build', 'package']:
            data = data.replace(m.group('base') + t + m.group('rest'), '${CONAN_MRPT_ROOT}')

        outp = open(path, 'w')
        outp.write(data)


    def package(self):
        pass

    def package_info(self):
        # Put CMake file here
        pass

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
