#include <Eigen/Core>
#include <Eigen/Geometry>

#include <cassert>
#include <cmath>
#include <iostream>

namespace {
constexpr double kTolerance = 1e-10;
constexpr double kPi = 3.14159265358979323846;

bool nearlyEqual(double lhs, double rhs, double tolerance = kTolerance) {
  return std::abs(lhs - rhs) < tolerance;
}

void testMatrixOperations() {
  Eigen::Matrix3d matrix_a;
  matrix_a << 1.0, 2.0, 3.0,
              4.0, 5.0, 6.0,
              7.0, 8.0, 10.0;

  Eigen::Matrix3d matrix_b = Eigen::Matrix3d::Identity();
  Eigen::Vector3d vector_x(1.0, 2.0, 3.0);

  Eigen::Matrix3d sum = matrix_a + matrix_b;
  Eigen::Vector3d product = matrix_a * vector_x;
  Eigen::Matrix3d inverse = matrix_a.inverse();

  assert(nearlyEqual(sum(0, 0), 2.0));
  assert(nearlyEqual(product(0), 14.0));
  assert((matrix_a * inverse).isApprox(Eigen::Matrix3d::Identity(), 1e-9));
}

void testEulerQuaternionRotation() {
  const double yaw = kPi / 6.0;
  const double pitch = kPi / 9.0;
  const double roll = kPi / 12.0;

  Eigen::AngleAxisd yaw_angle(yaw, Eigen::Vector3d::UnitZ());
  Eigen::AngleAxisd pitch_angle(pitch, Eigen::Vector3d::UnitY());
  Eigen::AngleAxisd roll_angle(roll, Eigen::Vector3d::UnitX());

  Eigen::Matrix3d rotation_matrix =
      (yaw_angle * pitch_angle * roll_angle).toRotationMatrix();
  Eigen::Quaterniond quaternion(rotation_matrix);
  Eigen::Vector3d euler_angles = rotation_matrix.eulerAngles(2, 1, 0);

  assert(rotation_matrix.isApprox(quaternion.toRotationMatrix(), 1e-10));
  assert(nearlyEqual(euler_angles[0], yaw));
  assert(nearlyEqual(euler_angles[1], pitch));
  assert(nearlyEqual(euler_angles[2], roll));
}

void testPoseTransform() {
  Eigen::Isometry3d transform = Eigen::Isometry3d::Identity();
  transform.rotate(Eigen::AngleAxisd(kPi / 2.0, Eigen::Vector3d::UnitZ()));
  transform.pretranslate(Eigen::Vector3d(1.0, 2.0, 3.0));

  Eigen::Vector3d point_local(1.0, 0.0, 0.0);
  Eigen::Vector3d point_world = transform * point_local;

  assert(point_world.isApprox(Eigen::Vector3d(1.0, 3.0, 3.0), 1e-10));
  assert((transform.inverse() * point_world).isApprox(point_local, 1e-10));
}
}  // namespace

int main() {
  testMatrixOperations();
  testEulerQuaternionRotation();
  testPoseTransform();

  std::cout << "All Eigen math tests passed." << std::endl;
  return 0;
}
