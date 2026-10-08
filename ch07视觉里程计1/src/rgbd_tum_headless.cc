// Headless RGB-D driver for the official ORB-SLAM3 library.
// The input format is the TUM RGB-D association file:
// rgb_timestamp rgb_path depth_timestamp depth_path.
#include <System.h>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include <filesystem>
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace fs = std::filesystem;

struct Frame {
  double timestamp;
  fs::path rgb;
  fs::path depth;
};

std::vector<Frame> ReadAssociations(const fs::path& sequence,
                                    const fs::path& associations) {
  std::ifstream input(associations);
  if (!input) throw std::runtime_error("Cannot open associations: " + associations.string());
  std::vector<Frame> frames;
  std::string line;
  while (std::getline(input, line)) {
    if (line.empty() || line[0] == '#') continue;
    std::istringstream row(line);
    double rgb_time, depth_time;
    std::string rgb, depth;
    if (!(row >> rgb_time >> rgb >> depth_time >> depth))
      throw std::runtime_error("Malformed association: " + line);
    frames.push_back({rgb_time, sequence / rgb, sequence / depth});
  }
  if (frames.empty()) throw std::runtime_error("No associated RGB-D frames");
  return frames;
}

int main(int argc, char** argv) {
  if (argc != 6) {
    std::cerr << "Usage: rgbd_tum_headless VOCAB TUM1_YAML SEQUENCE ASSOCIATIONS OUTPUT_DIR\n";
    return 2;
  }
  try {
    const fs::path output = argv[5];
    fs::create_directories(output);
    const auto frames = ReadAssociations(argv[3], argv[4]);
    std::ofstream states(output / "tracking_states.csv");
    if (!states) throw std::runtime_error("Cannot write tracking_states.csv");
    states << "timestamp,state,x,y,z\n" << std::fixed << std::setprecision(9);

    // false disables Pangolin's GUI; RGB-D gives metric-scale translation.
    ORB_SLAM3::System slam(argv[1], argv[2], ORB_SLAM3::System::RGBD, false);
    const float scale = slam.GetImageScale();
    int tracked = 0;
    for (size_t i = 0; i < frames.size(); ++i) {
      const auto started = std::chrono::steady_clock::now();
      cv::Mat rgb = cv::imread(frames[i].rgb.string(), cv::IMREAD_UNCHANGED);
      cv::Mat depth = cv::imread(frames[i].depth.string(), cv::IMREAD_UNCHANGED);
      if (rgb.empty() || depth.empty())
        throw std::runtime_error("Cannot load RGB/depth pair at index " + std::to_string(i));
      if (scale != 1.0f) {
        cv::resize(rgb, rgb, cv::Size(), scale, scale);
        cv::resize(depth, depth, cv::Size(), scale, scale, cv::INTER_NEAREST);
      }
      const Sophus::SE3f Tcw = slam.TrackRGBD(rgb, depth, frames[i].timestamp);
      const int state = slam.GetTrackingState();
      states << frames[i].timestamp << ',' << state;
      if (state == 2) {  // ORB-SLAM3 Tracking::OK
        const auto position = Tcw.inverse().translation();
        states << ',' << position.x() << ',' << position.y() << ',' << position.z();
        ++tracked;
      } else {
        states << ",,,";
      }
      states << '\n';
      // Keep roughly the dataset frame rate so mapping threads can catch up.
      if (i + 1 < frames.size()) {
        const double interval = frames[i + 1].timestamp - frames[i].timestamp;
        const double elapsed = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - started).count();
        if (interval > elapsed)
          std::this_thread::sleep_for(std::chrono::duration<double>(interval - elapsed));
      }
      if ((i + 1) % 100 == 0 || i + 1 == frames.size())
        std::cout << "Processed " << i + 1 << '/' << frames.size()
                  << " frames; tracked " << tracked << '\n';
    }
    slam.Shutdown();
    states.close();
    slam.SaveTrajectoryTUM((output / "CameraTrajectory.txt").string());
    slam.SaveKeyFrameTrajectoryTUM((output / "KeyFrameTrajectory.txt").string());
    std::cout << "Saved trajectory and tracking states to " << output << '\n';
    return tracked > 0 ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << "rgbd_tum_headless: " << error.what() << '\n';
    return 1;
  }
}
