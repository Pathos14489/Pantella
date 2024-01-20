@echo off
setlocal
set CMAKE_ARGS=""
set FORCE_CMAKE=0
echo nstalling llama-cpp-python for CPU
python3 -m pip install llama-cpp-python --no-deps --no-cache-dir --force-reinstall --upgrade
echo Done