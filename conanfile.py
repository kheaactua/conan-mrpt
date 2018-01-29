from conans import ConanFile, CMake, tools


class MrptConan(ConanFile):
    name = "mrpt"
    version = "1.5.5"
    license = "BSD"
    url = "http://www.mrpt.org/"
    description = "<Description of Mrpt here>"
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake"
    requires = (
        'Boost.Thread/[>=1.56]@bincrafters/stable',
        'Boost.System/[>=1.56]@bincrafters/stable',
        'eigen/[>=3.0.0]@3dri/stable',
        'flann/[>=1.6.8]@3dri/stable',
        'vtk/[>=5.6.1]@3dri/stable',
        'qhull/2015.2@3dri/stable',
        # glut
        # opencv
        'gtest/[>=1.8.0]@lasote/stable',
        'assimp/[>3.1]@3dri/stable',
        'zlib/[>1.2.11]@conan/stable',
        'pcl/[>1.7.0]@3dri/stable',
    )
    options = {"shared": [True, False]}
    default_options = "shared=False"

    def source(self):

        ext = "tar.xz" if self.settings.os == "Linux" else "zip"
        archive=f'mrpt-{self.version}.{ext}'
        archive_url=f'https://github.com/MRPT/mrpt/archive/{archive}'

        hashes = {
            '1.5.5.tar.gz': '3f74fecfe1a113c350332122553e1685',
            '1.5.5.zip':    '48c188d70a3844ab49036a05cf5786fd',
        }

        tools.download(url=archive_url, filename=archive)
        try:
            tools.check_md5(archive, hashes[archive])
        except ConanException as e:
            self.output.error(e)
            sys.exit(-1)

        # Extract it
        if ext == 'tar.xz':
            self.run(f"tar xf {archive}")
        else:
            tools.unzip(archive)
        shutil.move(f'mrpt-{self.version}', self.name)

    def system_requirements(self):
        pack_names = None
        if os_info.linux_distro == "ubuntu":
            # Minimal requirements
            # (removed from here because we provide our own: libopencv-dev,
            # libeigen3-dev, libgtest-dev)
            pack_names = [
                'build-essential', 'pkg-config', 'cmake', 'libwxgtk3.0-dev'
            ]

            # Additional
            # (removed from here because we provide our own: zlib1g-dev libassimp-dev
            pack_names = [
                'libftdi-dev', 'freeglut3-dev', '',
                'libusb-1.0-0-dev', 'libudev-dev', 'libfreenect-dev',
                'libdc1394-22-dev', 'libavformat-dev', 'libswscale-dev',
                'libjpeg-dev', 'libsuitesparse-dev', 'libpcap-dev',
                'liboctomap-dev'
            ]

            if self.settings.arch == "x86":
                full_pack_names = []
                for pack_name in pack_names:
                    full_pack_names += [pack_name + ":i386"]
                pack_names = full_pack_names

        if pack_names:
            installer = SystemPackageTool()
            installer.update() # Update the package database
            installer.install(" ".join(pack_names)) # Install the package

    def configure(self):
        self.options['boost'].shared = True

    def build(self):

        args = []

        args.append('-DCMAKE_CXX_FLAGS="-fPIC"')
        args.append('-DCMAKE_INSTALL_PREFIX:PATH=%s'self.package_folder)
        # args.append('-DCMAKE_BUILD_TYPE=${bld_type}')
        args.append('-DOpenCV_DIR:PATH=%s'%self.deps_cpp_info['opencv'].rootpath) # ${libs}/OpenCV/${OPENCV_VERSION}/share/OpenCV
        args.append('-DPCL_DIR:PATH=%s'self.deps_cpp_info['pcl'].rootpath) # ${libs}/PCL/${PCL_VERSION}/share/pcl-${short_pcl_version}')
        args.append('-DEIGEN_ROOT:PATH=%s'$self.deps_cpp_info['eigen'].rootpath) # ${libs}/Eigen/${EIGEN_VERSION}')
        args.append('-DEIGEN3_DIR:PATH=%s/share/eigen3/cmake'%self.deps_cpp_info['eigen'].rootpath)
        args.append('-DEIGEN_INCLUDE_DIR:PATH=%s/include/eigen3'%self.deps_cpp_info['eigen'].rootpath)
        args.append('-DBOOST_ROOT=%s'self.deps_cpp_info['boost'])
        args.append('-DFLANN_ROOT=%s'%self.deps_cpp_info['flann'].rootpath)
        args.append('-DEIGEN_INCLUDE_DIR:PATH=%s/include/eigen3'%self.deps_cpp_info['eigen'].rootpath)
        args.append('-DFLANN_INCLUDE_DIR:PATH=%s/include'%self.deps_cpp_info['flann'].rootpath)
        args.append('-DVTK_DIR=%s'%self.deps_cpp_info['vtk'].rootpath) # ${libs}/VTK/${VTK_VERSION}/${bld_type}/lib/cmake/vtk-${short_vtk_version}/')
        args.append('-DQHULL_INCLUDE_DIR:PATH=%s/include'%self.deps_cpp_info['qhull'].rootpath)
        args.append('-DQHULL_LIBRARY:FILEPATH=%s/lib/libqhull.so'%self.deps_cpp_info['qhull'].rootpath)
        # args.append('-DQHULL_LIBRARY_DEBUG=${libs}/qhull/${QHULL_VERSION}/lib/libqhull_d.so')
        args.append('-DGLUT_INCLUDE_DIR=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'include'))
        args.append('-DGLUT_glut_LIBRARY=%s'%os.path.join(self.deps_cpp_info['freeglut'].rootpath, 'lib', 'libglut.so'))
        args.append('-DZLIB_INCLUDE_DIR=%s'%os.path.join(seld.deps_cpp_info['zlib'].rootpath, 'include'))
        args.append('-DZLIB_LIBRARY_RELEASE=%s'%os.path.join(seld.deps_cpp_info['zlib'].rootpath, 'include', 'libz.so' if self.settings.os == 'Linux' else 'libz.dll'))
        args.append('-DGTEST_ROOT=%s'%self.deps_cpp_info['gtest'].rootpath)

        cmake = CMake(self)
        cmake.configure(source_folder="hello")
        cmake.build()

        # Fix up the CMake Find Script PCL generated
        self.output.info('Inserting Conan variables in to the PCL CMake Find script.')
        self.fixFindPackage(cmake.build_folder, vtk_cmake_rel_dir)

    def package(self):
        pass

    def package_info(self):
        # Put CMake file here
        pass

# vim: ts=4 sw=4 expandtab ffs=unix ft=python foldmethod=marker :
