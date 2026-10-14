[app]

# (str) Title of your application
title = Witchy Game

# (str) Package name
package.name = witchygame

# (str) Package domain (needed for android/ios packaging)
package.domain = org.witchygame

# (str) Source code where the main.py lives
source.dir = .

# (list) Source files to include (added png, jpg, kv, atlas)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of inclusions using pattern matching to ensure your assets folder is packaged
source.include_patterns = assets/*, assets/images/*

# (str) Application versioning
version = 0.1

# (list) Application requirements (Pinned to stable 3.11.8 to prevent compiler crashes)
requirements = python3==3.11.8,hostpython3==3.11.8,kivy

# (str) Supported orientations (landscape, portrait or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not (0 is false, 1 is true)
fullscreen = 1

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (bool) Auto-accept Android SDK licenses to prevent build freezing
android.accept_sdk_license = True


[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
