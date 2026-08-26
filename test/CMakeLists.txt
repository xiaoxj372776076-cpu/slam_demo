cmake_minimum_required(VERSION 3.10)
project(slam_eigen_pangolin_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Eigen3 REQUIRED)

add_executable(eigen_math_tests src/eigen_math_tests.cpp)
target_link_libraries(eigen_math_tests Eigen3::Eigen)

enable_testing()
add_test(NAME eigen_math_tests COMMAND eigen_math_tests)

find_package(Pangolin QUIET)

if(Pangolin_FOUND)
  find_package(GLEW REQUIRED)

  add_executable(eigen_pangolin_demo src/eigen_pangolin_demo.cpp)
  target_link_libraries(eigen_pangolin_demo Eigen3::Eigen ${Pangolin_LIBRARIES} GLEW::GLEW)
  target_include_directories(eigen_pangolin_demo PRIVATE ${Pangolin_INCLUDE_DIRS})
else()
  message(WARNING "Pangolin was not found. eigen_math_tests will build, but eigen_pangolin_demo is skipped.")
endif()
