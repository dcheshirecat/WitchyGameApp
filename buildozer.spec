[app]

# (str) Title of your application
title = Witchy Game

# (str) Package name
package.name = witchygame

# (str) Package domain (needed for android/ios packaging)
package.domain = org.witchygame

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching to ensure assets are packaged
source.include_patterns = assets/*, assets/images/*

# (str) Application versioning
version = 0.1

# (list) Application requirements (Use unpinned kivy so python-for-android uses its native recipe)
requirements = python3==3.11.8,hostpython3==3.11.8,kivy,pyjnius,android

# (str) Supported orientations (landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (list) The architectures to build for (arm64-v8a avoids cross-compilation linking errors)
android.archs = arm64-v8a

# (int) Target Android API
android.api = 33

# (int) Minimum API your APK will support
android.minapi = 24

# (bool) Auto-accept Android SDK licenses to prevent build freezing
android.accept_sdk_license = True


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1
