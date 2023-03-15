mkdir -p build
cd build
export Sina_DIR="../../cpp/build-clang/install/lib/cmake/sina"
cmake -C ../../cpp/CMake/host-configs/sina-linux-rhel7-ivybridge-clang@11.0.1.cmake -DCMAKE_TOOLCHAIN_FILE=../../cpp/CMake/Platform/toss_3_x86_64_clang.cmake .. -DCMAKE_INSTALL_PREFIX=install
make
