# Runner 타깃에 Swift 파일을 더한다 — pbxproj 를 손으로 고치지 않으려고.
#
# 이 프로젝트는 폴더 동기화 그룹이 아니라서 `ios/Runner/` 에 파일을 두는 것만으로는 컴파일되지 않는다.
# 쓰는 법(app/ 에서, xcodeproj 젬은 CocoaPods 것을 빌려 쓴다):
#   GEM_HOME=$(brew --prefix cocoapods)/libexec $(brew --prefix ruby)/bin/ruby tool/add_ios_file.rb VideoTranscoder.swift
# 저장하면서 젬이 무관한 줄(패키지 참조 주석·설정 키 순서)을 바꿀 수 있다 — git diff 로 보고 되돌린다.
require "xcodeproj"

name = ARGV.fetch(0)
project = Xcodeproj::Project.open(File.join(__dir__, "..", "ios", "Runner.xcodeproj"))
group = project.main_group["Runner"]
target = project.targets.find { |t| t.name == "Runner" }

if group.files.any? { |f| f.path == name }
  puts "이미 있다: #{name}"
else
  target.add_file_references([group.new_reference(name)])
  project.save
  puts "더했다: #{name}"
end
