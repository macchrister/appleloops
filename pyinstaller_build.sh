#!/bin/zsh


echo "This will build a version of appleloops that does not require the Python 3 framework to be installed."
echo "However there are caveats that apply."
echo " - You must build this on the minimum macOS version that you plan on installing content to"
echo " - If building on macOS 11+, there are errors that are generated when building relating to libraries not being found"
echo " - This will add a few extra seconds at the start of the script as the script is unzipped to a temporary location"
echo " - The resulting appleloops file is approximately 12MB to 14MB in size compared to a few KB for the zipbuild version"
echo ""
echo "The recommended build process is to use './'zipbuild.sh'"

vared -p 'If you are sure you wish to proceed, press Y/y [enter], else press N/n then [enter]: ' -c RESPONSE

if [ ${RESPONSE} = 'Y' -o ${RESPONSE} = 'y' ]; then
    /usr/bin/find . -type d -iname __pycache__ -exec rm -r {} \; 2>/dev/null

    /Library/Frameworks/Python.framework/Versions/Current/bin/pyinstaller \
        --distpath ./pyinstaller_builds/dist \
        --workpath ./pyinstaller_builds/build \
        --specpath ./pyinstaller_builds/spec \
        --onefile src/__main__.py \
        --name appleloops \
        --osx-bundle-identifier com.github.carlashley.appleloops \
        --add-data '../../src/loopslib/*:loopslib' \
        --add-data '../../src/loopslib/resources/*:loopslib/resources' \
        --clean
fi
