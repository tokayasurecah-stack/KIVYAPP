[app]
title = YT Downloader
package.name = ytdownloader
package.domain = org.tonybbosa
source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ico
version = 2.0.0
requirements = python3,kivy,yt-dlp,pillow
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 33
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True
presplash.filename = favicon (1).ico
icon.filename = favicon (1).ico

[buildozer]
log_level = 2
warn_on_root = 0
