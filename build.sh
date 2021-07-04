#!/bin/zsh

LOCAL_PYTHON=/usr/local/bin/python3
BUILD_DIR=dist/usr/local/bin
BUILD_OUT=${BUILD_DIR}/appleloops

if [ ${LOCAL_PYTHON} = '' ]; then
    /bin/echo 'Python 3 is required. Exiting.'
    exit 1
fi

# Clean any __pycache__ directories that might have been created during testing
/usr/bin/find . -type d -iname __pycache__ -exec rm -r {} \; 2>/dev/null

# To provide your own python path, just add '--python=/path/to/python' after './build'
# For example: ./build.sh --python="/usr/bin/env python3.7"
# or           ./build.sh --python="/usr/local/munki/python"
if [[ ! -z ${1} ]]; then
    DIST_CMD=$(echo /usr/local/bin/python3 -m zipapp src --compress --output ${BUILD_OUT} ${1})
else
    DIST_CMD=$(echo /usr/local/bin/python3 -m zipapp src --compress --output ${BUILD_OUT} --python=\"/usr/local/bin/python3\")
fi

# Clean up
/bin/rm ${BUILD_OUT} &> /dev/null

# Build
eval ${DIST_CMD}

if [ $? -eq 0 ]; then
    # If the file exists, we can build the pkg
    if [ -f ${BUILD_OUT} ]; then
        /bin/chmod +x ${BUILD_OUT}
        PKGTITLE="appleloops"
        PKG_VERSION=$(/usr/bin/awk -F ': ' '/version: / {print $NF}' ./src/loopslib/resources/configuration.yaml)
        PKGVERSION="${PKG_VERSION}"
        BUNDLEID="com.github.carlashley.appleloops"
        PROJECT="appleloops"

        if ! [ -f ./build/pkg ]; then
            /bin/mkdir -p ./build/pkg
        fi

        setopt +o nomatch  # Ignore no matches found for globs
        /bin/rm -f .build/pkg/appleloops-*.pkg &> /dev/null
        /usr/bin/pkgbuild --root ./dist/ --identifier ${BUNDLEID} \
            --version ${PKGVERSION} \
            --ownership recommended  \
            --preserve-xattr ./build/pkg/${PKGTITLE}-${PKGVERSION}.component.pkg
        /usr/bin/productbuild --identifier ${BUNDLEID} \
            --package ./build/pkg/${PKGTITLE}-${PKGVERSION}.component.pkg ./build/pkg/appleloops-${PKGVERSION}.pkg
        /bin/rm -f ./build/pkg/${PKGTITLE}-${PKGVERSION}.component.pkg &> /dev/null
    fi
else
    echo "Build failed."
fi
