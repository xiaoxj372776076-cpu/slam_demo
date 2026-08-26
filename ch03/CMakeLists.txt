cmake_minimum_required(VERSION 3.10)
project(ch03_eigen_pangolin_demo LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Eigen3 REQUIRED)

add_executable(eigen_math_tests src/eigen_math_tests.cpp)
target_link_libraries(eigen_math_tests Eigen3::Eigen)

enable_testing()
add_test(NAME eigen_math_tests COMMAND eigen_math_tests)

# Pangolin is optional so the Eigen tests can still be built on machines that
# only have the math dependency installed.
find_package(Pangolin QUIET)

if(Pangolin_FOUND)
  # Pangolin's OpenGL headers include GLEW on macOS/Homebrew builds, so link it
  # explicitly to make the demo portable across local environments.
  find_package(GLEW REQUIRED)

  add_executable(eigen_pangolin_demo src/eigen_pangolin_demo.cpp)
  target_link_libraries(eigen_pangolin_demo Eigen3::Eigen ${Pangolin_LIBRARIES} GLEW::GLEW)
  target_include_directories(eigen_pangolin_demo PRIVATE ${Pangolin_INCLUDE_DIRS})
else()
  message(WARNING "Pangolin was not found. eigen_math_tests will build, but eigen_pangolin_demo is skipped.")
endif()
