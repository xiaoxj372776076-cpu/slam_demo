cmake_minimum_required(VERSION 3.16)
project(ch07_orbslam3_rgbd_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(ORB_SLAM3_ROOT "" CACHE PATH "ORB-SLAM3 source/build directory")
if(NOT EXISTS "${ORB_SLAM3_ROOT}/include/System.h")
  message(FATAL_ERROR "Set ORB_SLAM3_ROOT to a built ORB-SLAM3 checkout")
endif()

find_package(OpenCV 4.4 REQUIRED COMPONENTS core imgcodecs imgproc)
find_package(Eigen3 REQUIRED)
find_package(Boost REQUIRED)
find_package(Pangolin REQUIRED)
find_library(ORB_SLAM3_LIBRARY NAMES ORB_SLAM3
  PATHS "${ORB_SLAM3_ROOT}/lib" NO_DEFAULT_PATH REQUIRED)

add_executable(rgbd_tum_headless src/rgbd_tum_headless.cc)
target_include_directories(rgbd_tum_headless PRIVATE
  "${ORB_SLAM3_ROOT}"
  "${ORB_SLAM3_ROOT}/include"
  "${ORB_SLAM3_ROOT}/include/CameraModels"
  "${ORB_SLAM3_ROOT}/Thirdparty/Sophus"
  ${Boost_INCLUDE_DIRS}
  ${Pangolin_INCLUDE_DIRS}
)
target_link_libraries(rgbd_tum_headless PRIVATE
  "${ORB_SLAM3_LIBRARY}" ${OpenCV_LIBS} Eigen3::Eigen ${Pangolin_LIBRARIES})

if(APPLE)
  set_target_properties(rgbd_tum_headless PROPERTIES
    BUILD_RPATH "${ORB_SLAM3_ROOT}/lib;${ORB_SLAM3_ROOT}/Thirdparty/DBoW2/lib;${ORB_SLAM3_ROOT}/Thirdparty/g2o/lib")
endif()
