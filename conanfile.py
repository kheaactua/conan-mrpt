import os, sys, shutil, re
from conans import ConanFile, CMake, tools
from conans.errors import ConanException


class MrptConan(ConanFile):
    """
    Tested with versions 1.4.0, 1.5.5.

    1.2.2 fails with 'cannot find -lQt5::Widgets'
    """

    name = 'mrpt'
    license = 'BSD'
    url = 'http://www.mrpt.org/'
    description = 'The Mobile Robot Programming Toolkit (MRPT) '
    settings = 'os', 'compiler', 'build_type', 'arch'
    generators = 'cmake'
    requires = (
        'eigen/[>=3.2.0]@ntc/stable',
        'vtk/[>=5.6.1]@ntc/stable',
        'freeglut/[>=3.0.0]@ntc/stable',
        'opencv/[>=2.4.9]@ntc/stable',
        'assimp/[>=3.1]@ntc/stable',
        'zlib/[>=1.2.11]@conan/stable',
        'pcl/[>=1.7.0]@ntc/stable',
        'qt/[>=5.3.2]@ntc/stable',
        'flann/[>=1.6.8]@ntc/stable',
        'boost/[>1.46]@ntc/stable',
    )
    options = {
        'shared':      [True, False],
        'build_tests': [True, False],
    }
    default_options = 'shared=True', 'build_tests=False'

    def configure(self):
        self.options['opencv'].shared = self.options.shared
        self.options['zlib'].shared = self.options.shared

    def source(self):

        ext = 'tar.gz'
        archive=f'{self.version}.{ext}'
        archive_url=f'https://github.com/MRPT/mrpt/archive/{archive}'

        hashes = {
            '1.5.5': '3f74fecfe1a113c350332122553e1685',
            '1.4.0': 'ca36688b2512a21dac27aadca34153ce',
            '1.2.2': '074cc4608515927811dec3d0744c75b6',
        }

        local_copy = os.path.join('/tmp', f'mrpt-{archive}')
        if os.path.exists(local_copy):
            shutil.copy(local_copy, os.path.join(self.source_folder, archive))
        else:
            tools.download(url=archive_url, filename=archive)
            try:
                tools.check_md5(archive, hashes[self.version])
            except ConanException as e:
                self.output.error(e)
                sys.exit(-1)

        tools.unzip(archive)
        shutil.move(f'mrpt-{self.version}', self.name)

        vtk_release = int(self.deps_cpp_info['vtk'].version.split('.')[0])
        if vtk_release < 7:
            # Need to add find_package(Qt5Widgets).  I think the HEAD of OpenCV
            # does this, but 1.5.5- doesn't.  I believe this is required because
            # VTK injects dependencies to it, and no matter how hard I try, I can't
            # seem to build without VTK or this dependency.  I don't recall
            # seeing this after VTK v7 though.
            self.output.info('Injecting a find_package(Qt5Widgets) due to VTK 6')
            file = os.path.join(self.name, 'cmakemodules/DeclareMRPTLib.cmake')
            with open(file) as f: data = f.read()
            data = 'find_package(Qt5Widgets)\n\n' + data
            with open(file, 'w') as f: f.write(data)


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

        mrpt_major = int(self.version.split('.')[1])
        vtk_major  = '.'.join(self.deps_cpp_info['vtk'].version.split('.')[:2])
        pcl_major  = '.'.join(self.deps_cpp_info['pcl'].version.split('.')[:2])

        args = []

        if self.options.shared:
            args.append('-DBUILD_SHARED_LIBS:BOOL=TRUE')
        args.append('-DBOOST_ROOT:PATH=%s'%self.deps_cpp_info['boost'].rootpath)
        args.append('-DBUILD_KINECT:BOOL=FALSE')
        args.append('-DMRPT_HAS_ASIAN_FONTS:BOOL=FALSE')
        args.append('-DBUILD_EXAMPLES:BOOL=FALSE')
        args.append('-DMRPT_HAS_ASIAN_FONTS:BOOL=FALSE')
        args.append('-DCMAKE_CXX_FLAGS="-fPIC"')
        args.append('-DBUILD_TESTING:BOOL=%s'%('TRUE' if self.options.build_tests else 'FALSE'))

        # Skipping xSens (3rd and 4th gen libs for xSens MT* devices)
        args.append('-DBUILD_XSENS_MT3:BOOL=FALSE')
        args.append('-DBUILD_XSENS_MT4:BOOL=FALSE')

        args.append('-DPCL_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['pcl'].rootpath, 'share', f'pcl-{pcl_major}'))
        args.append('-DOpenCV_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['opencv'].rootpath, 'share', 'OpenCV'))
        args.append('-DVTK_DIR:PATH=%s'%os.path.join(self.deps_cpp_info['vtk'].rootpath, 'lib', 'cmake', f'vtk-{vtk_major}'))

        args.append('-DGLUT_INCLUDE_DIR=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'include'))
        args.append('-DGLUT_glut_LIBRARY=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'lib', 'libglut.so'))

        args.append('-DQt5Widgets_DIR:PATH=%s'%  os.path.join(self.deps_cpp_info['qt'].rootpath, 'lib', 'cmake', 'Qt5Widgets'))

        args.append('-DZLIB_INCLUDE_DIR=%s'%os.path.join(self.deps_cpp_info['zlib'].rootpath, 'include'))
        if self.options.shared:
            libz = 'libz.so' if self.settings.os == 'Linux' else 'libz.dll'
        else:
            libz = 'libz.a' if self.settings.os == 'Linux' else 'libz.lib'
        args.append('-DZLIB_LIBRARY_RELEASE=%s'%os.path.join(self.deps_cpp_info['zlib'].rootpath, 'lib', libz))

        args.append('-DBUILD_ASSIMP:BOOL=FALSE')
        pkg_vars = {
            'PKG_CONFIG_eigen3_PREFIX': self.deps_cpp_info['eigen'].rootpath,
            'PKG_CONFIG_assimp_PREFIX': self.deps_cpp_info['assimp'].rootpath,
            'PKG_CONFIG_pcl_PREFIX':    self.deps_cpp_info['pcl'].rootpath,
            'PKG_CONFIG_flann_PREFIX':  self.deps_cpp_info['flann'].rootpath,
            'PKG_CONFIG_PATH': ':'.join([
                os.path.join(self.deps_cpp_info['eigen'].rootpath,  'share', 'pkgconfig'),
                os.path.join(self.deps_cpp_info['assimp'].rootpath, 'lib',   'pkgconfig'),
                os.path.join(self.deps_cpp_info['pcl'].rootpath,    'lib',   'pkgconfig'),
                os.path.join(self.deps_cpp_info['flann'].rootpath,  'lib',   'pkgconfig'),
            ]),
            'OpenCV_ROOT_DIR': self.deps_cpp_info['opencv'].rootpath,
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

        with open(path) as f: data = f.read()

        m = re.search(r'SET.MRPT_DIR "(?P<base>.*?)(?P<type>(build|package))(?P<rest>.*?(?="))', data)
        if not m:
            self.output.warn('Could not find MRPT source directory in CMake file')
            return
        for t in ['build', 'package']:
            data = data.replace(m.group('base') + t + m.group('rest'), '${CONAN_MRPT_ROOT}')


        mrpt_major = int(self.version.split('.')[1])
        if mrpt_major <= 2:
            # This CMake file pollutes the INCLUDE and LINK spaces, so we gotta
            # clean those out.

            data = '''#
# Note:  This file has been manually modified to not inject links/includes into
# the global scope, and to instead define MRPT_LIBRARIES and MRPT_INCLUDE_DIRS
# that can then be used by our OPAL_MRPT find script

''' + data

            m = re.search(r'INCLUDE_DIRECTORIES\("(?P<path>.*?eigen[^"]+)"\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "${CONAN_INCLUDE_DIRS_EIGEN}")')
            else:
                self.output.warn('Could not repair reference to Eigen include directory in MRPTConfig.cmake')

            m = re.search(r'INCLUDE_DIRECTORIES\(\${MRPT_CONFIG_DIR}\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "${MRPT_CONFIG_DIR}")')
            else:
                self.output.warn('Could not repair reference to MRPT CONFIG directory in MRPTConfig.cmake')

            m = re.search(r'LINK_DIRECTORIES\(""\)', data)
            if m:
                data = data.replace(m.group(0), '# ' + m.group(0))
            else:
                self.output.warn('Could not comment out empty link_directories directive in MRPTConfig.cmake')

            m = re.search(r'INCLUDE_DIRECTORIES\("(?P<suitesparse>[^"]+)"\) # SuiteSparse\w+', data)
            if m:
                # Note: We may want to replace this with a Conan package for SuiteSparse in the future
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "%s") # SuiteSparse_INCLUDE_DIRS'%m.group('suitesparse'))
            else:
                self.output.warn('Could not repair reference to SuiteSparse directory in MRPTConfig.cmake')

            m = re.search(r'INCLUDE_DIRECTORIES\("(?P<path>\${MRPT_LIBS_INCL_DIR}/\${MRPTLIB}/include)"\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "%s")'%m.group('path'))
            else:
                self.output.warn('Could not repair reference to MRPT include directory in MRPTConfig.cmake')

            m = re.search(r'LINK_DIRECTORIES\(\${wxWidgets_LIBRARY_DIRS}\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "%s")'%'list(APPEND MRPT_LINK_DIRECTORIES ${wxWidgets_LIBRARY_DIRS})')
            else:
                self.output.warn('Could not repair the link to wxWidget in MRPTConfig.cmake')

            m = re.search(r'(?P<first>LINK_DIRECTORIES\("/lib"\))\s+LINK_DIRECTORIES\("/lib"\)', data, re.MULTILINE)
            if m:
                data = data.replace(m.group(0), m.group('first'))
            else:
                self.output.warn('Could not remove the duplicate link directories in MRPTConfig.cmake')

            m = re.search(r'LINK_DIRECTORIES\((?P<lib>\${MRPT_DIR}/lib)\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_LINK_DIRECTORIES "%s")'%m.group('lib'))
            else:
                self.output.warn('Could not repair link to MRPT libs in MRPTConfig.cmake')

            data += '''

# Defining for forward-compatiblity
set(MRPT_LIBRARIES ${MRPT_LIBS})'''

        with open(path, 'w') as f: f.write(data)


    def package(self):
        pass

    def package_info(self):
        # Put CMake file here
        pass

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
