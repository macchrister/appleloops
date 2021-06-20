#!/bin/zsh

/Library/Frameworks/Python.framework/Versions/3.7/bin/pyinstaller \
    --onefile src/__main__.py \
    --name appleloops \
    --osx-bundle-identifier com.github.carlashley.appleloops \
    --add-data 'src/loopslib/*:loopslib'
