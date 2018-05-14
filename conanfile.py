#!/usr/bin/env python
# -*- coding: future_fstrings -*-
# -*- coding: utf-8 -*-

import os, sys, shutil, re, platform, glob
from conans import ConanFile, CMake, tools
from conans.model.version import Version
from conans.errors import ConanException
import conans.client.build.compiler_flags as cf


class MrptConan(ConanFile):
    """
    Tested with versions 1.2.2, 1.4.0, 1.5.5.
    """

    name        = 'mrpt'
    license     = 'BSD'
    url         = 'http://www.mrpt.org/'
    description = 'The Mobile Robot Programming Toolkit (MRPT) '
    settings    = 'os', 'compiler', 'build_type', 'arch', 'arch_build'
    requires    = (
        'eigen/[>=3.2.0]@ntc/stable',
        'vtk/[>=5.6.1]@ntc/stable',
        'freeglut/[>=3.0.0]@ntc/stable',
        'opencv/[>=2.4.9]@ntc/stable',
        'zlib/[>=1.2.11]@conan/stable',
        'qt/[>=5.3.2]@ntc/stable',
        'flann/[>=1.6.8]@ntc/stable',
        'boost/[>1.46]@ntc/stable',
        'libjpeg/9b@lasote/stable',
        'helpers/0.3@ntc/stable',
    )

    options = {
        'shared':      [True, False],
        'fPIC':        [True, False],
        'cxx11':       [True, False],
        'build_tests': [True, False],
    }
    default_options = (
        'shared=True',
        'fPIC=True',
        'cxx11=True',
        'build_tests=False',
    )

    def build_requirements(self):
        self.build_requires('pkg-config/0.29.2@ntc/stable')
        if self.settings.arch_build == 'x86':
            self.build_requires('cmake_installer/[>3.2.0,<=3.6.3]@conan/stable')
        else:
            self.build_requires('cmake_installer/[>3.2.0]@conan/stable')

    def requirements(self):
        if not ('Windows' == self.settings.os and 'x86' == self.settings.arch):
            # MRPT v1.2.2 just won't find assimp.lib on win32.
            if 'x86' == self.settings.arch and 'Linux' == self.settings.os:
                # On Linux 32, assimp seems to not be building with c++11, which
                # causes a bunch of problems
                self.requires('assimp/[>=3.1,<4.0]@ntc/stable')
            else:
                self.requires('assimp/[>=3.1]@ntc/stable')

        # Inexplicably, PCL is sometimes not found by MRPT (the include paths
        # aren't working despite being correct.)  So disabling PCL for now.
        # TODO Re-enable PCL.  This may have been a pkg-config issue
        # # Suddenly MRPT 1.2.2 no longer builds on Windows claiming an ambiguous
        # # type PointT in PbMapMaker.cpp.  As we don't use PCL MRPT functions
        # # right now, and MRPT has wasted an impressive amount of my time, I'm
        # # pushing off fixing this issue.
        # if (Version(str(self.version)) > '1.2.2') or (not 'Windows' == self.settings.os):
        #     self.requires('pcl/[>=1.7.0]@ntc/stable')

    def config_options(self):
        if self.settings.compiler == "Visual Studio":
            self.options.remove("fPIC")

    def configure(self):
        # I don't think specifying these is a good idea anymore.
        self.options['flann'].shared    = self.options.shared
        self.options['opencv'].shared   = self.options.shared
        self.options['boost'].shared    = self.options.shared
        self.options['freeglut'].shared = self.options.shared
        self.options['vtk'].shared      = self.options.shared
        self.options['pcl'].shared      = self.options.shared
        self.options['assimp'].shared   = self.options.shared
        self.options['opencv'].shared   = self.options.shared
        self.options['zlib'].shared     = self.options.shared
        self.options['libjpeg'].shared  = self.options.shared

        if self.settings.compiler != "Visual Studio":
            self.options['boost'].fPIC = True

        if (Version(str(self.version)) > '1.2.2') or (not 'Windows' == self.settings.os):
            self.options['pcl'].shared   = self.options.shared

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
            tools.check_md5(archive, hashes[self.version])

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

        # C1027 error
        tools.replace_in_file(
            file_path=os.path.join(self.name, 'CMakeLists.txt'),
            search='/Zm1000',
            replace='/Zm300',
        )

        if self.settings.compiler == 'gcc':
            import cmake_helpers
            cmake_helpers.wrapCMakeFile(os.path.join(self.source_folder, self.name), output_func=self.output.info)

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
            try:
                installer.update() # Update the package database
                installer.install(" ".join(pack_names)) # Install the package
            except ConanException:
                self.output.warn('Could not run system updates')

    def _set_up_cmake(self):
        """
        Normally this would be in build, but because we often have to
        re-run pacakging (MRPT has been annoying), and packaging is more or
        less done with cmake.install(), we need the CMake object to be
        available to us in both the build() and package() methods
        """

        vtk_major  = '.'.join(self.deps_cpp_info['vtk'].version.split('.')[:2])

        cmake = CMake(self)

        if 'fPIC' in self.options and self.options.fPIC:
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = 'ON'
        if self.options.cxx11:
            cmake.definitions['CMAKE_CXX_STANDARD'] = 11

        if self.settings.compiler == 'gcc':
            cmake.definitions['ADDITIONAL_CXX_FLAGS:STRING'] = ' '.join([
                '-frecord-gcc-switches',
                '-Wno-deprecated-declarations'
            ])

        # Reported as unused by cmake, but there is a message from the cmake output to use them
        cmake.definitions['BOOST_DYNAMIC:BOOL']        = 'TRUE' if self.options['boost'].shared else 'FALSE'
        cmake.definitions['BOOST_ROOT:PATH']           = self.deps_cpp_info['boost'].rootpath
        #

        cmake.definitions['BUILD_SHARED_LIBS:BOOL']    = 'TRUE' if self.options.shared else 'FALSE'
        cmake.definitions['BUILD_KINECT:BOOL']         = 'FALSE'
        cmake.definitions['MRPT_HAS_ASIAN_FONTS:BOOL'] = 'FALSE'
        cmake.definitions['BUILD_EXAMPLES:BOOL']       = 'FALSE'
        cmake.definitions['BUILD_TESTING:BOOL']        = 'TRUE' if self.options.build_tests else 'FALSE'

        # Skipping xSens (3rd and 4th gen libs for xSens MT* devices)
        cmake.definitions['BUILD_XSENS_MT3:BOOL'] = 'FALSE'
        cmake.definitions['BUILD_XSENS_MT4:BOOL'] = 'FALSE'

        if 'pcl' in self.deps_cpp_info.deps:
            cmake.definitions['PCL_DIR:PATH']    = self.deps_cpp_info['pcl'].resdirs[0]
        cmake.definitions['OpenCV_DIR:PATH']     = self.deps_cpp_info['opencv'].resdirs[0]
        cmake.definitions['VTK_DIR:PATH']        = os.path.join(self.deps_cpp_info['vtk'].rootpath, 'lib', 'cmake', f'vtk-{vtk_major}')

        cmake.definitions['GLUT_INCLUDE_DIR:PATH']  = os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'include')
        cmake.definitions['GLUT_glut_LIBRARY:PATH'] = os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'lib', 'libglut.so')

        cmake.definitions['Qt5Widgets_DIR:PATH'] = os.path.join(self.deps_cpp_info['qt'].rootpath, 'lib', 'cmake', 'Qt5Widgets')

        cmake.definitions['ZLIB_ROOT'] = self.deps_cpp_info['zlib'].rootpath

        if not ('Windows' == self.settings.os and 'x86' == self.settings.arch):
            # MRPT v1.2.2 just won't find assimp.lib on win32.
            # TODO I suspect this was an issue with assimp's pkg-config file.
            #      Now that that is fixed, this exception  "if not windows 32"
            #      exception # can probably be removed.
            cmake.definitions['BUILD_ASSIMP:BOOL'] = 'FALSE'
        env_vars = {
            'OpenCV_ROOT_DIR': self.deps_cpp_info['opencv'].rootpath,
        }

        # Include our own libjpeg so that the linking across different systems
        # isn't an issue
        cmake.definitions['JPEG_INCLUDE_DIR:PATH'] = os.path.join(self.deps_cpp_info['libjpeg'].rootpath, 'include')
        cmake.definitions['JPEG_LIBRARY:FILEPATH'] = os.path.join(self.deps_cpp_info['libjpeg'].rootpath, 'lib', 'libjpeg.so' if self.options['libjpeg'].shared else 'libjpeg.a')

        return cmake, env_vars

    def build(self):

        cmake, env_vars = self._set_up_cmake()

        # Debug
        s = '\nAdditional Environment:\n'
        for k,v in env_vars.items():
            s += ' - %s=%s\n'%(k, v)
        self.output.info(s)

        s = '\nRelated pkg-config Environment Variables:\n'
        for k,v in os.environ.items():
            if re.search('PKG_CONFIG', k):
                s += ' - %s=%s\n'%(k, v)
        self.output.info(s)

        s = '\nCMake Definitions:\n'
        for k,v in cmake.definitions.items():
            s += ' - %s=%s\n'%(k, v)
        self.output.info(s)

        with tools.environment_append(env_vars):
            cmake.configure(source_folder=self.name)
            cmake.build()

    def package(self):

        # Use cmake's install target
        cmake, env_vars = self._set_up_cmake()
        with tools.environment_append(env_vars):
            cmake.configure(source_folder=os.path.join(self.build_folder, self.name), build_folder=self.build_folder)
        cmake.install()

        # Fix up the CMake Find Script MRPT generated
        if 'Windows' == platform.system():
            cmake_src_file = os.path.join(self.build_folder, 'MRPTConfig.cmake')
        else:
            cmake_src_file = os.path.join(self.build_folder, 'unix-install', 'MRPTConfig.cmake')
        cmake_dst_file = os.path.join(self.package_folder, self.mrpt_cmake_rel_dir, 'MRPTConfig.cmake')
        self.output.info('Inserting Conan variables in to the MRPT CMake Find script at found at %s and writting to %s'%(cmake_src_file, cmake_dst_file))
        self._fixFindPackage(src=cmake_src_file, dst=cmake_dst_file)

    def package_info(self):
        # Add the directory with CMake.. Not sure if this is a good use of resdirs
        self.cpp_info.resdirs = [os.path.join(self.package_folder, self.mrpt_cmake_rel_dir)]

        # Populate the pkg-config environment variables
        with tools.pythonpath(self):
            from platform_helpers import appendPkgConfigPath

            pkg_config_path = os.path.join(self.package_folder, 'lib', 'pkgconfig')
            appendPkgConfigPath(cf.adjust_path(pkg_config_path), self.env_info)

            pc_files = glob.glob(cf.adjust_path(os.path.join(pkg_config_path, '*.pc')))
            for f in pc_files:
                p_name = re.sub(r'\.pc$', '', os.path.basename(f))
                p_name = re.sub(r'\W', '_', p_name.upper())
                setattr(self.env_info, f'PKG_CONFIG_{p_name}_PREFIX', cf.adjust_path(self.package_folder))

            appendPkgConfigPath(cf.adjust_path(pkg_config_path), self.env_info)

    @property
    def mrpt_cmake_rel_dir(self):
        """ Relative directory of the published (packaged) MRPTConfig.cmake file """

        if 'Windows' == platform.system():
            # On Windows, this CMake file is in a different place
            return ''
        else:
            return os.path.join('share', 'mrpt')

    def _fixFindPackage(self, src, dst):
        """
        Insert some variables into the MRPT find script generated in the
        build so that we can use it in our CMake scripts

        @param src Source path of the find script
        @param dst Destination (file we write to) of the find script
        """

        if not os.path.exists(src):
            self.output.warn('Could not fix non-existant file: %s'%src)
            return

        with open(src) as f: data = f.read()

        if re.search(r'CONAN', data):
            self.output.info('MRPTConfig.cmake file already patched with Conan variables')
            return

        m = re.search(r'get_filename_component.THIS_MRPT_CONFIG_PATH "..CMAKE_CURRENT_LIST_FILE." PATH.', data)
        if m:
            data = data.replace(m.group(0), 'set(THIS_MRPT_CONFIG_PATH ${CONAN_MRPT_ROOT})')
        else:
            m = re.search(r'SET.MRPT_DIR "(?P<base>.*?)(?P<type>(build|package))(?P<rest>.*?(?="))', data)
            if not m:
                self.output.warn('Could not find MRPT source directory in CMake file: %s'%src)
                return
            for t in ['build', 'package']:
                data = data.replace(m.group('base') + t + m.group('rest'), '${CONAN_MRPT_ROOT}')


        mrpt_version = Version(str(self.version))
        if mrpt_version <= '2':
            # This CMake file pollutes the INCLUDE and LINK spaces, so we gotta
            # clean those out.

            data = '''#
# Note:  This file has been manually modified to not inject links/includes into
# the global scope, and to instead define MRPT_LIBRARIES and MRPT_INCLUDE_DIRS
# that can then be used by our OPAL_MRPT find script

''' + data


            m = re.search(r'SET.MRPT_SOURCE_DIR "(.*)".', data)
            if m:
                # Source isn't installed, so no real point in fixing this..
                data = data.replace(m.group(0), 'SET(MRPT_SOURCE_DIR "%s")'%cf.adjust_path(self.source_folder))

            m = re.search(r'SET.MRPT_LIBS_INCL_DIR "(?P<CONAN_ROOT>(?P<base>.*?).(?P<type>(build|package)).(?P<hash>\w+).)(?P<rest>.*?(?="))".', data)
            if m:
                # This one is weird, though I swear this used to work, now it
                # points to a non-existent path.  Specifically, it points to
                # <base>/mrpt/libs, when stuff is found at <base>/libs.
                # So, do some checking here to see what should be the right path.
                lib_inc_path = None
                if os.path.exists(os.path.join(self.package_folder, *(m.group('rest').split('/')))):
                    lib_inc_path = m.group('rest')
                    self.output.info('Default MRPT_LIBS_INCL_DIR was found, using %s'%lib_inc_path)
                else:
                    # Check for the leading mrpt, and remove it
                    parts = m.group('rest').split('/')
                    if parts[0] == 'mrpt':
                        if not os.path.join(self.package_folder, *parts[1:]):
                            raise ConanException('Could not find MRPT_LIBS_INCL_DIR at %s or %s'%(m.group('rest'), '/'.join(parts[1:])))
                        lib_inc_path = '/'.join(parts[1:]) # cmake always prefers '/'
                        self.output.info('Modified MRPT_LIBS_INCL_DIR was found, using %s'%lib_inc_path)

                if lib_inc_path is None:
                    raise ConanException('Could not find suitable MRPT_LIBS_INCL_DIR')
                data = data.replace(m.group(0), 'SET(MRPT_LIBS_INCL_DIR "${CONAN_MRPT_ROOT}/%s")'%lib_inc_path)
            else:
                self.output.warn('Could not repair MRPT_LIBS_INCL_DIR variable')

            m = re.search(r'SET.MRPT_CONFIG_DIR "(?P<CONAN_ROOT>(?P<base>.*?).(?P<type>(build|package)).(?P<hash>\w+).)(?P<rest>.*?(?="))".', data)
            if m:
                # Similar to above, the specified path [on Windows],
                # <base>/include/mrpt-config/win32/ doesn't exist, and the
                # files seem to actually be in <base>/include/mrpt/mrpt-config/
                # So, check if the specified one exists, and if not, attempt the backup
                mrpt_config_path = None
                if os.path.exists(os.path.join(self.package_folder, *(m.group('rest').split('/')))):
                    mrpt_config_path = m.group('rest')
                    self.output.info('Default MRPT_CONFIG_DIR was found, using %s'%mrpt_config_path)
                else:
                    if os.path.exists(os.path.join(self.package_folder, 'include', 'mrpt', 'mrpt-config')):
                        mrpt_config_path = '/'.join(['include', 'mrpt', 'mrpt-config']) # cmake prefers '/'
                        self.output.info('Modified MRPT_CONFIG_DIR was found, using %s'%mrpt_config_path)

                if mrpt_config_path is None:
                    raise ConanException('Could not find suitable MRPT_CONFIG_DIR')

                data = data.replace(m.group(0), 'SET(MRPT_CONFIG_DIR "${CONAN_MRPT_ROOT}/%s")'%mrpt_config_path)
            else:
                self.output.warn('Could not repair MRPT_CONFIG_DIR variable')

            m = re.search(r'SET.MRPT_DIR "(?P<CONAN_ROOT>(?P<base>.*?).(?P<type>(build|package)).(?P<hash>\w+).)(?P<rest>.*?(?="))".', data)
            if m:
                data = data.replace(m.group(0), 'SET(MRPT_DIR "${CONAN_MRPT_ROOT}")')

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

            m = re.search(r'(?=\w)LINK_DIRECTORIES\(\${wxWidgets_LIBRARY_DIRS}\)', data)
            if m:
                data = data.replace(m.group(0), 'list(APPEND MRPT_INCLUDE_DIRS "%s")'%'${wxWidgets_LIBRARY_DIRS}')
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

            # Now, replace any free floating conan path, just in case some were missed here
            data = data.replace(self.package_folder, '${CONAN_MRPT_ROOT}')
            data = data.replace(cf.adjust_path(self.package_folder), '${CONAN_MRPT_ROOT}')

            data += '''

# Defining for forward-compatiblity
set(MRPT_LIBRARIES ${MRPT_LIBS})'''

        if not os.path.exists(os.path.dirname(dst)):
            # Not sure how this could not exist, but just in case..
            os.makedirs(os.path.dirname(dst))

        self.output.info('Outputting modified %s'%dst)
        with open(dst, 'w+') as f: f.write(data)

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
