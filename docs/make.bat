@ECHO OFF
pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build

if "%1" == "" goto help
if "%1" == "html"    goto html
if "%1" == "html-it" goto html-it
if "%1" == "clean"   goto clean

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:html
%SPHINXBUILD% -b html %SOURCEDIR% %BUILDDIR%/html/en -D language=en %SPHINXOPTS% %O%
echo.English docs: %BUILDDIR%/html/en/index.html
goto end

:html-it
%SPHINXBUILD% -b html %SOURCEDIR% %BUILDDIR%/html/it -D language=it %SPHINXOPTS% %O%
echo.Italian docs: %BUILDDIR%/html/it/index.html
goto end

:clean
rmdir /s /q %BUILDDIR%
goto end

:end
popd
