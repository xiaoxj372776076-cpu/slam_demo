#include <Eigen/Core>
#include <Eigen/Geometry>
#include <pangolin/pangolin.h>

#include <cmath>
#include <iostream>
#include <vector>

namespace {
std::vector<Eigen::Isometry3d> createCameraTrajectory() {
  std::vector<Eigen::Isometry3d> poses;
  poses.reserve(12);

  for (int i = 0; i < 12; ++i) {
    const double t = static_cast<double>(i) * 0.25;
    const double yaw = t;
    const double pitch = 0.15 * std::sin(t);
    const double roll = 0.10 * std::cos(t);

    Eigen::AngleAxisd yaw_angle(yaw, Eigen::Vector3d::UnitZ());
    Eigen::AngleAxisd pitch_angle(pitch, Eigen::Vector3d::UnitY());
    Eigen::AngleAxisd roll_angle(roll, Eigen::Vector3d::UnitX());
    Eigen::Quaterniond q = yaw_angle * pitch_angle * roll_angle;

    Eigen::Isometry3d pose = Eigen::Isometry3d::Identity();
    pose.rotate(q.normalized());
    pose.pretranslate(Eigen::Vector3d(
        0.25 * i,
        std::sin(t),
        0.5 * std::cos(t)));

    poses.push_back(pose);
  }

  return poses;
}

void printEigenExamples(const Eigen::Isometry3d& first_pose) {
  Eigen::Matrix3d matrix;
  matrix << 1.0, 2.0, 3.0,
            4.0, 5.0, 6.0,
            7.0, 8.0, 10.0;
  Eigen::Vector3d vector(1.0, 2.0, 3.0);

  Eigen::Matrix3d rotation = first_pose.rotation();
  Eigen::Quaterniond quaternion(rotation);
  Eigen::Vector3d euler_ypr = rotation.eulerAngles(2, 1, 0);

  std::cout << "Matrix A:\n" << matrix << "\n\n";
  std::cout << "Vector x: " << vector.transpose() << "\n";
  std::cout << "A * x: " << (matrix * vector).transpose() << "\n\n";
  std::cout << "First pose rotation matrix:\n" << rotation << "\n\n";
  std::cout << "First pose quaternion [x y z w]: "
            << quaternion.x() << " " << quaternion.y() << " "
            << quaternion.z() << " " << quaternion.w() << "\n";
  std::cout << "First pose Euler yaw-pitch-roll: "
            << euler_ypr.transpose() << "\n\n";
}

pangolin::OpenGlMatrix toOpenGlMatrix(const Eigen::Isometry3d& transform) {
  Eigen::Matrix4d matrix = transform.matrix();
  pangolin::OpenGlMatrix gl_matrix;

  // Pangolin/OpenGL expects column-major memory order. Eigen's default Matrix4d
  // is column-major, so this copy preserves the pose layout.
  for (int i = 0; i < 16; ++i) {
    gl_matrix.m[i] = matrix.data()[i];
  }

  return gl_matrix;
}

void drawCameraFrame(const Eigen::Isometry3d& pose, double axis_length) {
  pangolin::OpenGlMatrix matrix = toOpenGlMatrix(pose);

  glPushMatrix();
  glMultMatrixd(matrix.m);
  glLineWidth(3.0f);
  glBegin(GL_LINES);

  glColor3f(1.0f, 0.0f, 0.0f);
  glVertex3d(0.0, 0.0, 0.0);
  glVertex3d(axis_length, 0.0, 0.0);

  glColor3f(0.0f, 1.0f, 0.0f);
  glVertex3d(0.0, 0.0, 0.0);
  glVertex3d(0.0, axis_length, 0.0);

  glColor3f(0.0f, 0.0f, 1.0f);
  glVertex3d(0.0, 0.0, 0.0);
  glVertex3d(0.0, 0.0, axis_length);

  glEnd();
  glPopMatrix();
}

void drawTrajectory(const std::vector<Eigen::Isometry3d>& poses) {
  glLineWidth(2.0f);
  glColor3f(0.15f, 0.15f, 0.15f);
  glBegin(GL_LINE_STRIP);
  for (const auto& pose : poses) {
    Eigen::Vector3d p = pose.translation();
    glVertex3d(p.x(), p.y(), p.z());
  }
  glEnd();
}
}  // namespace

int main() {
  std::vector<Eigen::Isometry3d> poses = createCameraTrajectory();
  printEigenExamples(poses.front());

  pangolin::CreateWindowAndBind("Eigen + Pangolin SLAM Demo", 1024, 768);
  glEnable(GL_DEPTH_TEST);

  pangolin::OpenGlRenderState camera(
      pangolin::ProjectionMatrix(1024, 768, 500, 500, 512, 389, 0.1, 1000),
      pangolin::ModelViewLookAt(3.0, -6.0, 4.0, 1.2, 0.0, 0.0, pangolin::AxisZ));

  pangolin::Handler3D handler(camera);
  pangolin::View& display = pangolin::CreateDisplay()
      .SetBounds(0.0, 1.0, 0.0, 1.0, -1024.0f / 768.0f)
      .SetHandler(&handler);

  while (!pangolin::ShouldQuit()) {
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    display.Activate(camera);

    drawTrajectory(poses);
    for (const auto& pose : poses) {
      drawCameraFrame(pose, 0.18);
    }

    pangolin::FinishFrame();
  }

  return 0;
}
