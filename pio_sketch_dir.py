# Point each PlatformIO env at its own Arduino sketch folder
# (set via `custom_sketch_dir` in platformio.ini), so .ino files
# can stay in Arduino-IDE-compatible folders.
Import("env")

sketch = env.GetProjectOption("custom_sketch_dir")
env.Replace(PROJECT_SRC_DIR="$PROJECT_DIR/" + sketch)
