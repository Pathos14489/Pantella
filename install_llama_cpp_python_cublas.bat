@echo off
setlocal
set CMAKE_ARGS=-DLLAMA_CUBLAS=on 
set FORCE_CMAKE=1
set CUDA_VERSION=
for /f "tokens=1,2,3,4,5,6,7,8,9,10,11,12,13,14,15 delims= " %%a in ('nvcc --version') do (
    if "%%a"=="Cuda" (
        for /f "tokens=1 delims=," %%a in ("%%e") do (
            for /f "tokens=1,2 delims=." %%a in ("%%a") do (
                set CUDA_VERSION=%%a_%%b
            )
        )
    )
)
echo CUDA Version: %CUDA_VERSION%
echo %CMAKE_ARGS%
if "%CUDA_VERSION%"=="" (
    :: run the CPU version if CUDA is not installed
    echo CUDA not found, running CPU installer/updater  
    call llama_cpp_python_cpu.bat
) else (
    echo Installing llama-cpp-python for CUDA
    python3 -m pip install llama-cpp-python --no-deps --no-cache-dir --force-reinstall --upgrade 
    :: 0.2.28 because the latest version broke GPU support temporarily
    echo Done
)